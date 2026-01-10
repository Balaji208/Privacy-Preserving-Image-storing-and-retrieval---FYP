"""
Secure Image Storage Pipeline
==============================
Orchestrates: Image Encryption → Feature Extraction → DeepHash → LSH → FHE → Redis

Input: User uploaded image (path or bytes)
Output: Redis storage with encrypted data + metadata
"""

import numpy as np
import tenseal as ts
import json
import time
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import redis
import hashlib
from datetime import datetime

# Import all modules
from image_encryption.image_encryptor import ImageEncryptor
from feature_extractor import ConvNeXtFeatureExtractor
from deephashing import DeepHashGenerator
from lsh_tokenization.pipeline.index_builder import LSHIndexer  # FIXED: Changed from LSHIndexBuilder
from lsh_tokenization.config.lsh_config import LSHConfig
from hsm.hsm_manager import get_hsm_manager
from image_encryption.utils.image_io import read_image_bytes

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Metadata for stored image."""
    image_id: str
    original_filename: str
    upload_timestamp: float
    image_size_bytes: int
    image_hash_sha256: str
    encryption_metadata: Dict
    deephash_sum: int
    lsh_tokens: list  # Changed from lsh_bucket_id
    fhe_ciphertext_size: int
    processing_time_ms: float


class SecureImageProcessor:
    """
    Complete image processing pipeline.
    
    Pipeline stages:
    1. Image Encryption (Kyber + AES-GCM)
    2. Feature Extraction (ConvNeXt-V2)
    3. DeepHash Generation (256-bit binary)
    4. LSH Bucketing (Redis storage)
    5. FHE Encryption (TenSEAL BFV)
    6. Redis Storage (encrypted + metadata)
    """
    
    def __init__(
        self,
        convnext_model_path: str = './models/convnext_state_dict_only.pt',
        deephash_model_path: str = './models/deephash_state_dict_only.pt',
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        tenant_id: str = 'default_tenant'
    ):
        """Initialize all pipeline components."""
        logger.info("Initializing Secure Image Processor...")
        
        self.tenant_id = tenant_id
        
        # 1. Image Encryptor
        self.image_encryptor = ImageEncryptor()
        logger.info("✓ Image Encryptor loaded")
        
        # 2. Feature Extractor
        self.feature_extractor = ConvNeXtFeatureExtractor(
            model_path=convnext_model_path
        )
        logger.info("✓ Feature Extractor loaded")
        
        # 3. DeepHash Generator
        self.hash_generator = DeepHashGenerator(
            model_path=deephash_model_path
        )
        logger.info("✓ DeepHash Generator loaded")
        
        # 4. Redis Client
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False  # Binary mode for encrypted data
        )
        self.redis_client.ping()
        logger.info("✓ Redis connected")
        
        # 5. LSH Indexer (using existing Redis client)
        lsh_config = LSHConfig()
        
        # Get HMAC key from HSM
        try:
            hsm = get_hsm_manager()
            hmac_key = hsm.retrieve_secret("HMAC_MASTER_KEY")
            logger.info("✓ HMAC key loaded from HSM")
        except Exception as e:
            logger.warning(f"HSM unavailable, using default key: {e}")
            # Fallback: generate deterministic key (NOT for production)
            hmac_key = hashlib.sha256(b"default_hmac_key_for_testing").digest()
        
        self.lsh_indexer = LSHIndexer(
            redis_client=self.redis_client,
            hmac_key=hmac_key,
            config=lsh_config,
            use_token_cache=True
        )
        logger.info("✓ LSH Indexer initialized")
        
        # 6. FHE Context (TenSEAL BFV)
        self.fhe_context = self._create_fhe_context()
        logger.info("✓ FHE Context created")
        
        logger.info("✅ All components initialized successfully")
    
    def _create_fhe_context(self) -> ts.Context:
        """Create FHE context with 128-bit security."""
        context = ts.context(
            ts.SCHEME_TYPE.BFV,
            poly_modulus_degree=4096,
            plain_modulus=1032193
        )
        context.generate_galois_keys()
        return context
    
    def process_image(
        self,
        image_path: str,
        image_id: Optional[str] = None
    ) -> Tuple[str, ImageMetadata]:
        """
        Process image through complete pipeline.
        
        Args:
            image_path: Path to input image
            image_id: Optional custom image ID (auto-generated if None)
            
        Returns:
            Tuple of (image_id, metadata)
        """
        start_time = time.time()
        image_path = Path(image_path)
        
        # Generate image ID if not provided
        if image_id is None:
            image_id = self._generate_image_id(image_path)
        
        logger.info(f"Processing image: {image_path.name} (ID: {image_id})")
        
        # Get image size
        image_size = image_path.stat().st_size
        
        # Compute SHA256 hash of original image
        image_sha256 = self._compute_sha256(image_path)
        
                # ================================================================
        # STAGE 1: Image Encryption
        # ================================================================
        logger.info("[1/5] Encrypting image...")
        
        # Read image bytes
        image_bytes = read_image_bytes(str(image_path))
        
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        # Encrypt with proper parameters
        encrypted_json = self.image_encryptor.encrypt_image(
            image_bytes=image_bytes,
            image_id=image_id,
            user_id='default_user',  # TODO: Get from user context
            timestamp=timestamp
        )
        logger.info(f"  ✓ Image encrypted: {len(json.dumps(encrypted_json)):,} bytes")

        
        # ================================================================
        # STAGE 2: Feature Extraction
        # ================================================================
        logger.info("[2/5] Extracting features...")
        features = self.feature_extractor.extract(str(image_path))
        logger.info(f"  ✓ Features extracted: shape={features.shape}")
        
        # ================================================================
        # STAGE 3: DeepHash Generation
        # ================================================================
        logger.info("[3/5] Generating DeepHash...")
        deephash = self.hash_generator.generate(features)
        
        # Convert to uint8 for LSH (LSH expects uint8)
        if deephash.dtype != np.uint8:
            deephash_uint8 = deephash.astype(np.uint8)
        else:
            deephash_uint8 = deephash
        
        # Convert to int64 for FHE
        deephash_int64 = deephash_uint8.astype(np.int64)
        
        deephash_sum = int(np.sum(deephash_int64))
        logger.info(f"  ✓ DeepHash generated: {deephash.shape}, sum={deephash_sum}")
        
        # ================================================================
        # STAGE 4: LSH Indexing
        # ================================================================
        logger.info("[4/5] Adding to LSH index...")
        
        # Add to LSH index
        success = self.lsh_indexer.add(
            binary_hash=deephash_uint8,
            tenant_id=self.tenant_id,
            hash_id=image_id
        )
        
        if not success:
            logger.warning("  ⚠ LSH indexing partially failed")
        
        # Get the tokens for this hash (for metadata)
        from lsh_tokenization.simhash.simhash_generator import SimHashGenerator
        simhash_gen = SimHashGenerator(self.lsh_indexer.config)
        bucket_ids = simhash_gen.generate_bucket_ids(deephash_uint8)
        
        logger.info(f"  ✓ LSH indexed: {len(bucket_ids)} buckets")
        
        # ================================================================
        # STAGE 5: FHE Encryption of DeepHash
        # ================================================================
        logger.info("[5/5] FHE encrypting DeepHash...")
        fhe_encrypted = ts.bfv_vector(self.fhe_context, deephash_int64.tolist())
        fhe_bytes = fhe_encrypted.serialize()
        logger.info(f"  ✓ FHE encrypted: {len(fhe_bytes):,} bytes")
        
        # ================================================================
        # STAGE 6: Store in Redis
        # ================================================================
        logger.info("Storing in Redis...")
        
        # Create metadata
        processing_time = (time.time() - start_time) * 1000  # ms
        metadata = ImageMetadata(
            image_id=image_id,
            original_filename=image_path.name,
            upload_timestamp=time.time(),
            image_size_bytes=image_size,
            image_hash_sha256=image_sha256,
            encryption_metadata=encrypted_json.get('metadata', {}),
            deephash_sum=deephash_sum,
            lsh_tokens=[str(bid) for bid in bucket_ids],  # Store bucket IDs
            fhe_ciphertext_size=len(fhe_bytes),
            processing_time_ms=processing_time
        )
        
        # Store in Redis with organized keys
        self._store_in_redis(
            image_id=image_id,
            encrypted_image_json=encrypted_json,
            fhe_encrypted_hash=fhe_bytes,
            metadata=metadata
        )
        
        logger.info(f"✅ Image processed successfully in {processing_time:.2f} ms")
        logger.info(f"   Image ID: {image_id}")
        logger.info(f"   LSH Buckets: {len(bucket_ids)}")
        logger.info(f"   FHE Size: {len(fhe_bytes):,} bytes")
        
        return image_id, metadata
    
    def _store_in_redis(
        self,
        image_id: str,
        encrypted_image_json: Dict,
        fhe_encrypted_hash: bytes,
        metadata: ImageMetadata
    ):
        """Store all data in Redis with organized keys."""
        
        # Key naming convention
        # img:encrypted:{id} - Encrypted image JSON
        # img:fhe:{id} - FHE encrypted hash
        # img:meta:{id} - Metadata
        # img:index:{tenant} - Set of all image IDs for tenant
        
        pipe = self.redis_client.pipeline()
        
        # 1. Store encrypted image (as JSON string)
        encrypted_key = f"img:encrypted:{image_id}"
        pipe.set(encrypted_key, json.dumps(encrypted_image_json))
        
        # 2. Store FHE encrypted hash (binary)
        fhe_key = f"img:fhe:{image_id}"
        pipe.set(fhe_key, fhe_encrypted_hash)
        
        # 3. Store metadata (as JSON)
        meta_key = f"img:meta:{image_id}"
        pipe.set(meta_key, json.dumps(asdict(metadata)))
        
        # 4. Add to tenant index set
        pipe.sadd(f"img:index:{self.tenant_id}", image_id)
        
        # 5. Set expiration (optional, 30 days)
        expiration_seconds = 30 * 24 * 60 * 60  # 30 days
        pipe.expire(encrypted_key, expiration_seconds)
        pipe.expire(fhe_key, expiration_seconds)
        pipe.expire(meta_key, expiration_seconds)
        
        # Execute pipeline
        pipe.execute()
        
        logger.info(f"  ✓ Stored in Redis: {image_id}")
        logger.info(f"    - {encrypted_key}")
        logger.info(f"    - {fhe_key}")
        logger.info(f"    - {meta_key}")
    
    def retrieve_image_data(self, image_id: str) -> Dict:
        """
        Retrieve all data for an image.
        
        Args:
            image_id: Image identifier
            
        Returns:
            Dictionary with all stored data
        """
        encrypted_key = f"img:encrypted:{image_id}"
        fhe_key = f"img:fhe:{image_id}"
        meta_key = f"img:meta:{image_id}"
        
        # Retrieve from Redis
        encrypted_json_str = self.redis_client.get(encrypted_key)
        fhe_bytes = self.redis_client.get(fhe_key)
        meta_json_str = self.redis_client.get(meta_key)
        
        if not all([encrypted_json_str, fhe_bytes, meta_json_str]):
            raise ValueError(f"Image {image_id} not found in Redis")
        
        return {
            'image_id': image_id,
            'encrypted_image': json.loads(encrypted_json_str),
            'fhe_encrypted_hash': fhe_bytes,
            'metadata': json.loads(meta_json_str)
        }
    
    def query_similar_images(
        self,
        query_image_path: str,
        top_k: int = 10
    ) -> list:
        """
        Find similar images using LSH.
        
        Args:
            query_image_path: Path to query image
            top_k: Number of results to return
            
        Returns:
            List of candidate image IDs
        """
        # Extract features and generate hash
        features = self.feature_extractor.extract(query_image_path)
        query_hash = self.hash_generator.generate(features)
        
        if query_hash.dtype != np.uint8:
            query_hash = query_hash.astype(np.uint8)
        
        # Query LSH index
        candidates = self.lsh_indexer.query(
            binary_hash=query_hash,
            tenant_id=self.tenant_id,
            deduplicate=True
        )
        
        return candidates[:top_k]
    
    def decrypt_fhe_hash(self, fhe_bytes: bytes) -> np.ndarray:
        """Decrypt FHE encrypted hash."""
        fhe_vector = ts.bfv_vector_from(self.fhe_context, fhe_bytes)
        decrypted = np.array(fhe_vector.decrypt(), dtype=np.int64)
        return decrypted
    
    def get_all_images(self) -> list:
        """Get all stored image IDs for this tenant."""
        image_ids = self.redis_client.smembers(f"img:index:{self.tenant_id}")
        return [img_id.decode('utf-8') for img_id in image_ids]
    
    def delete_image(self, image_id: str):
        """Delete all data for an image."""
        keys = [
            f"img:encrypted:{image_id}",
            f"img:fhe:{image_id}",
            f"img:meta:{image_id}"
        ]
        
        # Remove from tenant index
        self.redis_client.srem(f"img:index:{self.tenant_id}", image_id)
        
        # Get metadata to find hash for LSH deletion
        meta_key = f"img:meta:{image_id}"
        meta_json = self.redis_client.get(meta_key)
        
        # Delete from LSH index
        if meta_json:
            metadata = json.loads(meta_json)
            # Would need to reconstruct hash to delete from LSH
            # For now, LSH entry will remain (can be cleaned up later)
        
        # Delete all keys
        self.redis_client.delete(*keys)
        logger.info(f"✓ Deleted image: {image_id}")
    
    def _generate_image_id(self, image_path: Path) -> str:
        """Generate unique image ID."""
        timestamp = str(int(time.time() * 1000000))
        filename = image_path.stem
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
        total_images = self.redis_client.scard(f"img:index:{self.tenant_id}")
        
        # Get LSH stats
        lsh_stats = self.lsh_indexer.get_stats()
        
        return {
            'tenant_id': self.tenant_id,
            'total_images': total_images,
            'lsh_stats': lsh_stats,
            'redis_memory_used': self.redis_client.info('memory')['used_memory_human']
        }


# ============================================================================
# Helper Functions
# ============================================================================

def process_single_image(image_path: str, tenant_id: str = 'default') -> str:
    """
    Convenience function to process a single image.
    
    Args:
        image_path: Path to image file
        tenant_id: Tenant identifier
        
    Returns:
        Image ID
    """
    processor = SecureImageProcessor(tenant_id=tenant_id)
    image_id, metadata = processor.process_image(image_path)
    return image_id


def process_batch(image_paths: list, tenant_id: str = 'default') -> list:
    """
    Process multiple images in batch.
    
    Args:
        image_paths: List of image file paths
        tenant_id: Tenant identifier
        
    Returns:
        List of results
    """
    processor = SecureImageProcessor(tenant_id=tenant_id)
    results = []
    
    for img_path in image_paths:
        try:
            image_id, metadata = processor.process_image(img_path)
            results.append({
                'success': True,
                'image_id': image_id,
                'path': img_path
            })
        except Exception as e:
            logger.error(f"Failed to process {img_path}: {e}")
            results.append({
                'success': False,
                'path': img_path,
                'error': str(e)
            })
    
    return results
