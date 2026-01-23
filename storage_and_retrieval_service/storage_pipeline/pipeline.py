"""
Secure Image Storage Pipeline
==============================
Complete pipeline with Redis LSH + Azure Blob Storage + Optional Table Metadata

Flow (Updated for v4.0):
1. Image → Image Encryption (Kyber + AES-GCM)
2. Image → Feature Extraction (ConvNeXt-V2, 512D)
3. Features → DeepHash v4.0 (512D → 256-bit, direct mode, no PCA)
4. DeepHash → FHE Encryption (~432KB)
5. DeepHash → LSH Indexing → Redis (bucket_token → [fhe_ct_token])
6. FHE CT + encryption_json → Azure Blob (with FHE_CT embedded)
7. Optional: Metadata → Azure Table (for fast lookups)
"""

import numpy as np
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
from .storage.azure_blob_store import AzureBlobKVStore
from .storage.azure_table_store import AzureTableMetadataStore

logger = logging.getLogger(__name__)


class SecureImagePipeline:
    """
    Complete secure image storage pipeline with DeepHash v4.0.
    
    Storage Schema:
    ---------------
    Redis LSH:
        Key: HMAC(tenant_id:table_idx:bucket_id)
        Value: [HMAC(FHE_CT1 || image_id1), ...]
    
    Azure Blob:
        Blob Name: HMAC(FHE_CT || image_id).json
        Content: {
            ...encryption_json fields,
            "fhe_ciphertext": "base64_encoded",
            "fhe_ciphertext_size": 432154
        }
    
    Azure Table (Optional):
        PartitionKey: HMAC(FHE_CT || image_id)[:4]
        RowKey: HMAC(FHE_CT || image_id)
        blob_name: Reference to blob
        image_id: For quick lookup
    """
    
    def __init__(
        self,
        azure_config: AzureStorageConfig,
        convnext_model_path: str = './models/convnext_v2_best_phase1.pt',
        deephash_model_path: str = './models/deephash_v4_statedict.pt',
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        tenant_id: str = 'default_tenant',
        disable_redis: bool = False,
        use_table_metadata: bool = False,
        device: str = 'cuda'
    ):
        """
        Initialize pipeline with v4.0 models.
        
        Args:
            azure_config: Azure storage configuration
            convnext_model_path: Path to ConvNeXt v2 model
            deephash_model_path: Path to DeepHash v4.0 model
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            tenant_id: Tenant identifier
            disable_redis: Disable Redis LSH indexing
            use_table_metadata: Enable Azure Table metadata storage
            device: Device for ML models ('cuda' or 'cpu')
        """
        logger.info("=" * 70)
        logger.info("Initializing Secure Image Storage Pipeline (v4.0)")
        logger.info("=" * 70)
        
        self.tenant_id = tenant_id
        self.disable_redis = disable_redis
        self.use_table_metadata = use_table_metadata
        self.device = device
        
        # Initialize processors
        logger.info("\n[1/7] Initializing processors...")
        
        self.encryption_processor = EncryptionProcessor()
        
        self.feature_processor = FeatureProcessor(
            model_path=convnext_model_path,
            device=device
        )
        
        self.hash_processor = HashProcessor(
            model_path=deephash_model_path,
            device=device
        )
        
        self.fhe_processor = FHEProcessor()
        
        logger.info("✅ All processors initialized")
        logger.info("  - Image Encryption: Kyber-1024 + AES-256-GCM")
        logger.info("  - Feature Extraction: ConvNeXt-V2 (512D)")
        logger.info("  - Deep Hashing: v4.0 Direct Mode (512D → 256-bit, no PCA)")
        logger.info("  - FHE: BFV scheme (~432KB ciphertexts)")
        
        # Load HMAC key from HSM
        logger.info("\n[2/7] Loading HMAC key from HSM...")
        try:
            from hsm.hsm_manager import get_hsm_manager
            hsm = get_hsm_manager()
            self.hmac_key = hsm.retrieve_secret("LSH_HMAC_KEY")
            logger.info(f"✅ HMAC key loaded ({len(self.hmac_key)} bytes)")
        except Exception as e:
            logger.warning(f"HSM unavailable, using fallback key: {e}")
            self.hmac_key = hashlib.sha256(b"fallback_hmac_key_for_testing").digest()
        
        # Initialize Azure Blob Storage
        logger.info("\n[3/7] Initializing Azure Blob Storage...")
        self.azure_blob_store = AzureBlobKVStore(
            connection_string=azure_config.connection_string,
            hmac_key=self.hmac_key,
            container_name=azure_config.container_name
        )
        logger.info("✅ Azure Blob Storage initialized")
        
        # Optional: Initialize Azure Table Storage for metadata
        self.azure_table_store = None
        if use_table_metadata:
            logger.info("\n[4/7] Initializing Azure Table Storage (metadata)...")
            self.azure_table_store = AzureTableMetadataStore(
                connection_string=azure_config.connection_string,
                hmac_key=self.hmac_key
            )
            logger.info("✅ Azure Table metadata store initialized")
        else:
            logger.info("\n[4/7] Azure Table Storage disabled (metadata indexing off)")
        
        # Initialize Redis for LSH
        if not self.disable_redis:
            logger.info("\n[5/7] Initializing Redis for LSH...")
            try:
                import redis
                from lsh_tokenization.pipeline.index_builder import LSHIndexer
                from lsh_tokenization.config.lsh_config import LSHConfig
                
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False
                )
                self.redis_client.ping()
                logger.info("✅ Redis connected")
                
                lsh_config = LSHConfig(
                    hash_length=256,
                    num_tables=6,
                    bits_per_table=12,
                    random_seed=42
                )
                
                self.lsh_indexer = LSHIndexer(
                    redis_client=self.redis_client,
                    hmac_key=self.hmac_key,
                    config=lsh_config,
                    use_token_cache=True
                )
                logger.info("✅ LSH Indexer initialized")
                
            except Exception as e:
                logger.warning(f"Redis unavailable, disabling LSH: {e}")
                self.disable_redis = True
        else:
            logger.info("\n[5/7] Redis disabled (skip LSH)")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ PIPELINE INITIALIZED SUCCESSFULLY (v4.0)")
        logger.info("=" * 70 + "\n")
    
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
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Processing: {image_path.name}")
        logger.info(f"Image ID: {image_id}")
        logger.info(f"{'=' * 70}")
        
        image_size = image_path.stat().st_size
        image_sha256 = self._compute_sha256(image_path)
        
        # Stage 1: Image Encryption
        logger.info("\n[1/6] Encrypting image (Kyber + AES-GCM)...")
        encryption_json = self.encryption_processor.encrypt(
            str(image_path), image_id
        )
        logger.info(f"  ✅ Encrypted: {len(json.dumps(encryption_json)):,} bytes")
        
        # Stage 2: Feature Extraction
        logger.info("\n[2/6] Extracting features (ConvNeXt-V2)...")
        features = self.feature_processor.extract(str(image_path))
        logger.info(f"  ✅ Features: {features.shape} (512D)")
        
        # Stage 3: DeepHash Generation (v4.0 direct mode)
        logger.info("\n[3/6] Generating DeepHash (v4.0 direct mode)...")
        binary_hash = self.hash_processor.generate(features)
        
        if binary_hash.ndim > 1:
            binary_hash = binary_hash.squeeze()
        
        deephash_sum = int(np.sum(binary_hash))
        logger.info(f"  ✅ DeepHash: {binary_hash.shape}, ones={deephash_sum}/256")
        logger.info(f"  Mode: Direct (512D → 256-bit, no PCA)")
        
        # Stage 4: FHE Encryption
        logger.info("\n[4/6] FHE encrypting DeepHash...")
        fhe_bytes = self.fhe_processor.encrypt(binary_hash)
        logger.info(f"  ✅ FHE CT: {len(fhe_bytes):,} bytes")
        
        # Stage 5: LSH Indexing (Redis)
        lsh_bucket_count = 0
        if not self.disable_redis:
            try:
                logger.info("\n[5/6] LSH indexing (Redis)...")
                success = self.lsh_indexer.add_fhe_ct(
                    binary_hash=binary_hash,
                    tenant_id=self.tenant_id,
                    fhe_ct=fhe_bytes,
                    image_id=image_id
                )
                
                if success:
                    lsh_bucket_count = self.lsh_indexer.config.num_tables
                    logger.info(f"  ✅ LSH indexed: {lsh_bucket_count} buckets")
                else:
                    logger.warning("  ⚠️ LSH indexing failed")
            
            except Exception as e:
                logger.warning(f"  ⚠️ LSH indexing error: {e}")
        else:
            logger.info("\n[5/6] LSH indexing skipped (Redis disabled)")
        
        # Stage 6: Azure Blob Storage (with FHE_CT embedded)
        logger.info("\n[6/6] Storing in Azure Blob...")
        blob_name = self.azure_blob_store.put(
            fhe_ciphertext=fhe_bytes,
            image_id=image_id,
            encryption_json=encryption_json
        )
        logger.info(f"  ✅ Stored in Azure Blob")
        logger.info(f"  Blob Name: {blob_name[:32]}...")
        
        # Optional: Store metadata in Table Storage
        if self.use_table_metadata and self.azure_table_store:
            try:
                blob_size = len(json.dumps(encryption_json)) + len(fhe_bytes)
                self.azure_table_store.put(
                    fhe_ciphertext=fhe_bytes,
                    image_id=image_id,
                    blob_name=blob_name,
                    blob_size=blob_size
                )
                logger.info(f"  ✅ Metadata stored in Azure Table")
            except Exception as e:
                logger.warning(f"  ⚠️ Table metadata storage failed: {e}")
        
        # Create metadata
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"✅ PROCESSING COMPLETE: {processing_time:.2f} ms")
        logger.info(f"{'=' * 70}\n")
        
        metadata = ImageMetadata(
            image_id=image_id,
            original_filename=image_path.name,
            upload_timestamp=time.time(),
            image_size_bytes=image_size,
            image_sha256=image_sha256,
            encryption_metadata=encryption_json.get('metadata', {}),
            deephash_sum=deephash_sum,
            lsh_tokens=[],
            fhe_ciphertext_size=len(fhe_bytes),
            processing_time_ms=processing_time,
            azure_partition_key=blob_name[:4],
            azure_row_key=blob_name
        )
        
        return image_id, metadata
    
    def retrieve_and_decrypt(
        self,
        fhe_ciphertext: bytes,
        image_id: str
    ) -> Optional[Dict]:
        """Retrieve encrypted image data by FHE ciphertext + image_id."""
        data = self.azure_blob_store.get(fhe_ciphertext, image_id)
        
        if not data:
            return None
        
        retrieved_fhe_ct = data['fhe_ciphertext']
        decrypted_hash = self.fhe_processor.decrypt(retrieved_fhe_ct)
        
        return {
            'fhe_ciphertext': retrieved_fhe_ct,
            'encryption_json': data['value'],
            'image_id': image_id,
            'decrypted_hash': decrypted_hash,
            'blob_name': data['blob_name']
        }
    
    def retrieve_by_image_id(self, image_id: str) -> Optional[Dict]:
        """Retrieve by image_id (uses Table Storage if enabled)."""
        if self.use_table_metadata and self.azure_table_store:
            metadata = self.azure_table_store.get_by_image_id(image_id)
            if metadata:
                data = self.azure_blob_store.get_by_blob_name(metadata['blob_name'])
                if data:
                    return {
                        'encryption_json': data['value'],
                        'fhe_ciphertext': data['fhe_ciphertext'],
                        'image_id': image_id,
                        'blob_name': data['blob_name']
                    }
        
        data = self.azure_blob_store.get_by_image_id(image_id)
        if not data:
            return None
        
        return {
            'encryption_json': data['value'],
            'fhe_ciphertext': data['fhe_ciphertext'],
            'image_id': image_id,
            'blob_name': data['blob_name']
        }
    
    def retrieve_by_blob_name(self, blob_name: str) -> Optional[Dict]:
        """Retrieve by blob name (HMAC token)."""
        data = self.azure_blob_store.get_by_blob_name(blob_name)
        
        if not data:
            return None
        
        return {
            'encryption_json': data['value'],
            'fhe_ciphertext': data['fhe_ciphertext'],
            'blob_name': blob_name
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
            'pipeline_version': '4.0',
            'total_blobs': self.azure_blob_store.count_blobs(),
            'disable_redis': self.disable_redis,
            'use_table_metadata': self.use_table_metadata,
            'feature_extractor': 'ConvNeXt-V2 (512D)',
            'hash_model': 'DeepHash v4.0 (direct mode, no PCA)',
            'hash_architecture': '512D → [1024, 512] → 256-bit',
            'similarity_threshold': '66 bits',
            'device': self.device
        }
        
        if not self.disable_redis and hasattr(self, 'lsh_indexer'):
            stats['lsh_stats'] = self.lsh_indexer.get_stats()
        
        return stats
    
    def list_images(self, max_results: int = 10) -> list:
        """List stored images."""
        return self.azure_blob_store.list_blobs(max_results)
