"""
Token Generator for Query Pipeline
===================================
Generates LSH tokens from binary hash
"""

import logging
import numpy as np
from typing import List

logger = logging.getLogger(__name__)

class TokenGenerator:
    """Generates LSH tokens from binary hash."""
    
    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        """Initialize LSH components."""
        logger.info("[TokenGenerator] Initializing LSH components...")
        
        # Import from same modules as storage_pipeline
        import redis
        from lsh_tokenization.simhash.simhash_generator import SimHashGenerator
        from lsh_tokenization.tokenization.hmac_tokenizer import HMACTokenizer
        from lsh_tokenization.config.lsh_config import LSHConfig
        
        # Load HMAC key from HSM
        try:
            from hsm.hsm_manager import get_hsm_manager
            hsm = get_hsm_manager()
            self.hmac_key = hsm.retrieve_secret("LSH_HMAC_KEY")
            logger.info(f"[TokenGenerator] ✓ HMAC key loaded from HSM ({len(self.hmac_key)} bytes)")
        except Exception as e:
            logger.warning(f"[TokenGenerator] HSM unavailable, using fallback: {e}")
            import hashlib
            self.hmac_key = hashlib.sha256(b"fallback_hmac_key_for_testing").digest()
        
        # LSH config (must match storage pipeline!)
        self.config = LSHConfig(
            hash_length=256,
            num_tables=6,
            bits_per_table=12,
            random_seed=42
        )
        
        # SimHash generator
        self.simhash_generator = SimHashGenerator(self.config)
        logger.info(f"[TokenGenerator] ✓ SimHash generator initialized")
        logger.info(f"[TokenGenerator]   Config: {self.config.num_tables} tables, {self.config.bits_per_table} bits/table")
        
        # HMAC tokenizer
        self.hmac_tokenizer = HMACTokenizer(self.hmac_key)
        logger.info("[TokenGenerator] ✓ HMAC tokenizer initialized")
        
        # Redis client (for verification)
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False
        )
        self.redis_client.ping()
        
        logger.info("[TokenGenerator] ✓ Ready")
    
    def generate(self, binary_hash: np.ndarray, tenant_id: str = "user_001") -> List[str]:
        """
        Generate LSH tokens from binary hash.
        
        Args:
            binary_hash: (256,) array of 0/1
            tenant_id: Tenant identifier
            
        Returns:
            List of HMAC tokens (hex strings)
        """
        if binary_hash.shape != (256,):
            raise ValueError(f"Expected 256-bit hash, got {binary_hash.shape}")
        
        logger.debug(f"[TokenGenerator] Generating tokens from {binary_hash.shape[0]}-bit hash...")
        
        # Generate bucket IDs using SimHash
        bucket_ids = self.simhash_generator.generate_bucket_ids(binary_hash)
        logger.debug(f"[TokenGenerator] ✓ Generated {len(bucket_ids)} bucket IDs")
        
        # Generate HMAC tokens (BATCH METHOD)
        tokens = self.hmac_tokenizer.tokenize_batch(
            tenant_id=tenant_id,
            bucket_ids=bucket_ids
        )
        
        logger.debug(f"[TokenGenerator] ✓ Generated {len(tokens)} HMAC tokens")
        if tokens:
            logger.debug(f"[TokenGenerator] Token preview: {tokens[0][:16]}...")
        
        return tokens

    def get_config(self) -> dict:
        """Get LSH configuration."""
        return {
            'num_tables': self.config.num_tables,
            'bits_per_table': self.config.bits_per_table,
            'hash_length': self.config.hash_length,
            'random_seed': self.config.random_seed
        }
