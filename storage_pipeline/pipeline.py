"""
Secure Image Storage Pipeline
==============================
Main pipeline orchestrator with SHA256(FHE_CT) Azure Table Storage
"""

import numpy as np
import base64
import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Dict

from .config.azure_config import AzureStorageConfig
from .models.metadata import ImageMetadata
from .processors.encryption_processor import EncryptionProcessor
from .processors.feature_processor import FeatureProcessor
from .processors.hash_processor import HashProcessor
from .processors.fhe_processor import FHEProcessor
from .storage.azure_table_store import AzureTableKVStore  # Updated import

from lsh_tokenization.pipeline.index_builder import LSHIndexer
from lsh_tokenization.config.lsh_config import LSHConfig
from lsh_tokenization.simhash.simhash_generator import SimHashGenerator
from hsm.hsm_manager import get_hsm_manager

logger = logging.getLogger(__name__)

class SecureImagePipeline:
    """
    Complete image processing pipeline with Azure Table Storage.
    
    Pipeline stages:
    1. Image Encryption (Kyber + AES-GCM) → encryption_json
    2. Feature Extraction (ConvNeXt-V2)
    3. DeepHash Generation (256-bit)
    4. LSH Indexing (Redis)
    5. FHE Encryption (TenSEAL BFV) → 88KB fhe_bytes  
    6. Azure Storage: SHA256(fhe_bytes) → encryption_json + fhe_bytes
    """
    
    def __init__(
        self,
        azure_config: AzureStorageConfig,
        convnext_model_path: str = './models/convnext_state_dict_only.pt',
        deephash_model_path: str = './models/deephash_state_dict_only.pt',
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        tenant_id: str = 'default_tenant',
        disable_redis: bool = False  # Option to disable Redis
    ):
        """Initialize all pipeline components."""
        logger.info("Initializing Secure Image Pipeline...")
        
        self.tenant_id = tenant_id
        self.disable_redis = disable_redis
        
        # Initialize processors
        logger.info("✓ Initializing processors...")
        self.encryption_processor = EncryptionProcessor()
        self.feature_processor = FeatureProcessor(convnext_model_path)
        self.hash_processor = HashProcessor(deephash_model_path)
        self.fhe_processor = FHEProcessor()
        
        # Initialize Azure Table Storage (SHA256 keys)
        logger.info("✓ Initializing Azure Table Storage...")
        self.azure_store = AzureTableKVStore(
            connection_string=azure_config.connection_string
        )
        
        # Initialize Redis for LSH (with fallback)
        if not self.disable_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db,
                    decode_responses=False
                )
                self.redis_client.ping()
                logger.info("✓ Redis connected for LSH")
                
                # Initialize LSH Indexer
                lsh_config = LSHConfig()
                try:
                    hsm = get_hsm_manager()
                    hmac_key = hsm.retrieve_secret("HMAC_MASTER_KEY")
                except Exception as e:
                    logger.warning(f"HSM unavailable, using default key: {e}")
                    hmac_key = hashlib.sha256(b"default_hmac_key_for_testing").digest()
                
                self.lsh_indexer = LSHIndexer(
                    redis_client=self.redis_client,
                    hmac_key=hmac_key,
                    config=lsh_config,
                    use_token_cache=True
                )
                logger.info("✓ LSH Indexer initialized")
            except Exception as e:
                logger.warning(f"Redis unavailable, disabling LSH: {e}")
                self.disable_redis = True
        
        logger.info("✅ Pipeline initialized successfully")
    
    def process_image(
        self,
        image_path: str,
        image_id: Optional[str] = None
    ) -> Tuple[str, ImageMetadata]:
        """
        Process image through complete pipeline.
        
        Args:
            image_path: Path to input image
            image_id: Optional custom image ID
            
        Returns:
            Tuple of (image_id, metadata)
        """
        start_time = time.time()
        image_path = Path(image_path)
        
        if image_id is None:
            image_id = self._generate_image_id(image_path)
        
        logger.info(f"Processing image: {image_path.name} (ID: {image_id})")
        
        image_size = image_path.stat().st_size
        image_sha256 = self._compute_sha256(image_path)
        
        # Stage 1: Image Encryption (YOUR exact JSON format)
        logger.info("[1/6] Encrypting image...")
        encryption_json = self.encryption_processor.encrypt(
            str(image_path), image_id
        )
        logger.info(f"   ✓ Encrypted: {len(json.dumps(encryption_json))} bytes")
        
        # Stage 2: Feature Extraction
        logger.info("[2/6] Extracting features...")
        features = self.feature_processor.extract(str(image_path))
        logger.info(f"   ✓ Features: {features.shape}")
        
        # Stage 3: DeepHash Generation
        logger.info("[3/6] Generating DeepHash...")
        binary_hash = self.hash_processor.generate(features)
        deephash_sum = int(np.sum(binary_hash))
        logger.info(f"   ✓ DeepHash: sum={deephash_sum}")
        
        # Stage 4: LSH Indexing (skippable)
        lsh_tokens = []
        if not self.disable_redis:
            try:
                logger.info("[4/6] Adding to LSH index...")
                self.lsh_indexer.add(
                    binary_hash=binary_hash,
                    tenant_id=self.tenant_id,
                    hash_id=image_id
                )
                simhash_gen = SimHashGenerator(self.lsh_indexer.config)
                bucket_ids = simhash_gen.generate_bucket_ids(binary_hash)
                lsh_tokens = [str(bid) for bid in bucket_ids]
                logger.info(f"   ✓ LSH indexed: {len(lsh_tokens)} buckets")
            except Exception as e:
                logger.warning(f"LSH indexing failed: {e}")
        
        # Stage 5: FHE Encryption
        logger.info("[5/6] FHE encrypting DeepHash...")
        fhe_bytes = self.fhe_processor.encrypt(binary_hash)
        logger.info(f"   ✓ FHE: {len(fhe_bytes):,} bytes")
        
        # Stage 6: Azure Table Storage - SHA256(FHE) → encryption_json + FHE
        logger.info("[6/6] Storing in Azure Table Storage...")
        partition_key, row_key = self.azure_store.put(
            fhe_ciphertext=fhe_bytes,  # Key generation
            value=encryption_json      # YOUR exact JSON format
        )
        
        logger.info(f"✅ Processing complete in {(time.time()-start_time)*1000:.2f} ms")
        logger.info(f"   PartitionKey: {partition_key}")
        logger.info(f"   RowKey: {row_key}")
        logger.info(f"   Image ID: {image_id}")
        
        # Create metadata
        processing_time = (time.time() - start_time) * 1000
        metadata = ImageMetadata(
            image_id=image_id,
            original_filename=image_path.name,
            upload_timestamp=time.time(),
            image_size_bytes=image_size,
            image_sha256=image_sha256,
            encryption_metadata=encryption_json.get('metadata', {}),
            deephash_sum=deephash_sum,
            lsh_tokens=lsh_tokens,
            fhe_ciphertext_size=len(fhe_bytes),
            processing_time_ms=processing_time,
            azure_partition_key=partition_key,
            azure_row_key=row_key
        )
        
        return image_id, metadata
    
    def retrieve_and_decrypt(self, fhe_bytes: bytes) -> Optional[Dict]:
        """
        Retrieve + Decrypt complete data by FHE ciphertext.
        
        Returns:
        {
            'fhe_ciphertext': bytes,     # Ready for FHE decrypt
            'encryption_json': dict,     # Your image encryption JSON
            'image_id': str,
            'decrypted_hash': np.array,  # Decrypted DeepHash
            'row_key': str
        }
        """
        data = self.azure_store.get(fhe_bytes)
        if not data:
            return None
        
        # Decrypt FHE hash
        decrypted_hash = self.fhe_processor.decrypt(data['fhe_ciphertext'])
        
        return {
            'fhe_ciphertext': data['fhe_ciphertext'],
            'encryption_json': data['value'],  # Your exact JSON
            'image_id': data['image_id'],
            'decrypted_hash': decrypted_hash,
            'row_key': data['row_key']
        }
    
    def retrieve_by_image_id(self, image_id: str) -> Optional[Dict]:
        """Retrieve by image_id (user-facing)."""
        data = self.azure_store.get_by_image_id(image_id)
        if not data:
            return None
        
        # Decrypt FHE hash
        decrypted_hash = self.fhe_processor.decrypt(data['fhe_ciphertext'])
        
        return {
            'fhe_ciphertext': data['fhe_ciphertext'],
            'encryption_json': data['value'],
            'image_id': data['image_id'],
            'decrypted_hash': decrypted_hash
        }
    
    def retrieve_by_row_key(self, row_key: str) -> Optional[Dict]:
        """Retrieve by 44-char row key."""
        data = self.azure_store.get_by_row_key(row_key)
        if not data:
            return None
        
        decrypted_hash = self.fhe_processor.decrypt(data['fhe_ciphertext'])
        return {
            'fhe_ciphertext': data['fhe_ciphertext'],
            'encryption_json': data['value'],
            'image_id': data['image_id'],
            'decrypted_hash': decrypted_hash
        }
    
    def _generate_image_id(self, image_path: Path) -> str:
        """Generate unique image ID."""
        timestamp = str(int(time.time() * 1000000))
        filename = image_path.stem.replace(' ', '_')
        return f"{filename}_{timestamp}"
    
    def _compute_sha256(self, image_path: Path) -> str:
        """Compute SHA256 hash of image file."""
        sha256 = hashlib.sha256()
        with open(image_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def get_statistics(self) -> Dict:
        """Get pipeline statistics."""
        stats = {
            'tenant_id': self.tenant_id,
            'total_images': self.azure_store.count_entities(),
            'disable_redis': self.disable_redis
        }
        if not self.disable_redis and hasattr(self, 'lsh_indexer'):
            stats['lsh_stats'] = self.lsh_indexer.get_stats()
        return stats
    
    def list_images(self, max_results: int = 10) -> list:
        """List stored images."""
        return self.azure_store.list_image_ids(max_results)
