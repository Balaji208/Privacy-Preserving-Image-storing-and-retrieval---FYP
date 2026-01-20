"""
LSH Index Builder Pipeline
===========================

Main pipeline orchestrating LSH bucketing, tokenization, and FHE CT storage.
"""

import numpy as np
from typing import Optional, List, Dict
import logging
import redis

from ..config.lsh_config import LSHConfig
from ..simhash.simhash_generator import SimHashGenerator
from ..tokenization.hmac_tokenizer import HMACTokenizer, TokenCache
from ..storage.redis_index import RedisIndex
from ..utils.bit_utils import BitUtils
from ..utils.fhe_ct_tokenizer import FHECTTokenizer

logger = logging.getLogger(__name__)


class LSHIndexer:
    """
    Complete LSH indexing pipeline with FHE CT token storage.
    
    Architecture:
        1. SimHash bucket generation from DeepHash output
        2. HMAC tokenization of bucket IDs
        3. Redis storage: BUCKET_TOKEN → [HMAC(FHE_CT1), HMAC(FHE_CT2), ...]
    
    Storage Schema:
        Redis Key: HMAC(tenant_id:table_idx:bucket_id)
        Redis Value: List of HMAC(FHE_CT, image_id)
    
    This design matches Azure Table Storage where:
        PartitionKey = HMAC(FHE_CT, image_id)
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        hmac_key: bytes,
        config: Optional[LSHConfig] = None,
        use_token_cache: bool = True,
        token_cache_size: int = 10000
    ):
        """
        Initialize LSH indexer with FHE CT tokenizer.
        
        Args:
            redis_client: Connected Redis client
            hmac_key: 256-bit HMAC master key (from HSM)
            config: LSH configuration
            use_token_cache: Enable token caching
            token_cache_size: Maximum cached tokens
        """
        self.config = config or LSHConfig()
        
        # Initialize components
        self.simhash_generator = SimHashGenerator(self.config)
        self.bucket_tokenizer = HMACTokenizer(hmac_key)  # For bucket IDs
        self.fhe_ct_tokenizer = FHECTTokenizer(hmac_key)  # For FHE CTs
        self.redis_index = RedisIndex(redis_client, self.config)
        
        # Optional token cache
        self.token_cache = None
        if use_token_cache:
            self.token_cache = TokenCache(max_size=token_cache_size)
        
        logger.info(
            f"Initialized LSH indexer with FHE CT tokenization: "
            f"L={self.config.num_tables}, K={self.config.bits_per_table}"
        )
    
    def add_fhe_ct(
        self,
        binary_hash: np.ndarray,
        tenant_id: str,
        fhe_ct: bytes,
        image_id: str
    ) -> bool:
        """
        Add FHE ciphertext to the LSH index.
        
        Workflow:
            1. Generate L bucket IDs from DeepHash using SimHash
            2. Tokenize bucket IDs: HMAC(tenant_id:table_idx:bucket_id)
            3. Tokenize FHE CT: HMAC(FHE_CT, image_id)
            4. Store in Redis: bucket_token → [fhe_ct_token]
        
        Args:
            binary_hash: DeepHash output (256 bits as numpy array)
            tenant_id: Tenant identifier for multi-tenancy
            fhe_ct: FHE ciphertext bytes (~88 KB)
            image_id: Image identifier (used as salt)
        
        Returns:
            True if successfully added to all buckets
        
        Example:
            >>> success = indexer.add_fhe_ct(
            ...     binary_hash=deephash_output,  # 256-bit array
            ...     tenant_id="hospital_A",
            ...     fhe_ct=fhe_ciphertext_bytes,  # ~88 KB
            ...     image_id="IMG_001"
            ... )
        """
        BitUtils.validate_binary_hash(binary_hash, self.config.hash_length)
        
        try:
            # Step 1: Generate LSH bucket IDs from DeepHash
            bucket_ids = self.simhash_generator.generate_bucket_ids(binary_hash)
            
            logger.debug(
                f"Generated {len(bucket_ids)} bucket IDs for image_id={image_id}"
            )
            
            # Step 2: Tokenize bucket IDs
            bucket_tokens = self._get_bucket_tokens(tenant_id, bucket_ids)
            
            # Step 3: Tokenize FHE CT with image_id as salt
            fhe_ct_token = self.fhe_ct_tokenizer.tokenize_fhe_ct(fhe_ct, image_id)
            
            logger.debug(
                f"FHE CT token: {fhe_ct_token[:16]}... "
                f"(CT size: {len(fhe_ct):,} bytes)"
            )
            
            # Step 4: Store FHE CT token in Redis under each bucket
            success_count = 0
            for bucket_token in bucket_tokens:
                success = self.redis_index.add_fhe_ct_token(
                    bucket_token=bucket_token,
                    fhe_ct_token=fhe_ct_token
                )
                if success:
                    success_count += 1
            
            logger.info(
                f"Added FHE CT for image_id={image_id} to "
                f"{success_count}/{len(bucket_tokens)} buckets (tenant={tenant_id})"
            )
            
            return success_count == len(bucket_tokens)
            
        except Exception as e:
            logger.error(f"Failed to add FHE CT to index: {e}")
            return False
    
    def query_fhe_ct_tokens(
        self,
        binary_hash: np.ndarray,
        tenant_id: str,
        deduplicate: bool = True
    ) -> List[str]:
        """
        Query the index for candidate FHE CT tokens.
        
        Returns HMAC(FHE_CT, image_id) tokens that can be used
        to look up encrypted images in Azure Table Storage.
        
        Args:
            binary_hash: Query DeepHash (256 bits)
            tenant_id: Tenant identifier
            deduplicate: Remove duplicate tokens
        
        Returns:
            List of FHE CT HMAC tokens for Azure Table lookup
        
        Example:
            >>> query_hash = deephash_output  # 256-bit array
            >>> fhe_ct_tokens = indexer.query_fhe_ct_tokens(
            ...     query_hash, "hospital_A"
            ... )
            >>> 
            >>> # Use tokens to retrieve from Azure Table
            >>> for token in fhe_ct_tokens:
            ...     entity = azure_table.get_entity(
            ...         partition_key=token,
            ...         row_key=...
            ...     )
        """
        BitUtils.validate_binary_hash(binary_hash, self.config.hash_length)
        
        try:
            # Step 1: Generate bucket IDs
            bucket_ids = self.simhash_generator.generate_bucket_ids(binary_hash)
            
            # Step 2: Get bucket tokens
            bucket_tokens = self._get_bucket_tokens(tenant_id, bucket_ids)
            
            # Step 3: Retrieve FHE CT tokens from Redis
            fhe_ct_tokens = self.redis_index.get_fhe_ct_tokens(
                bucket_tokens=bucket_tokens,
                deduplicate=deduplicate
            )
            
            logger.info(
                f"Query returned {len(fhe_ct_tokens)} candidate FHE CT tokens "
                f"from {len(bucket_tokens)} buckets (tenant={tenant_id})"
            )
            
            return fhe_ct_tokens
            
        except Exception as e:
            logger.error(f"Failed to query index: {e}")
            return []
    
    def _get_bucket_tokens(
        self,
        tenant_id: str,
        bucket_ids: List[int]
    ) -> List[str]:
        """Get bucket tokens (with optional caching)."""
        tokens = []
        
        for table_idx, bucket_id in enumerate(bucket_ids):
            # Check cache first
            if self.token_cache is not None:
                cache_key = (tenant_id, bucket_id, table_idx)
                cached_token = self.token_cache.get(cache_key)
                
                if cached_token is not None:
                    tokens.append(cached_token)
                    continue
            
            # Compute bucket token
            token = self.bucket_tokenizer.tokenize(tenant_id, bucket_id, table_idx)
            tokens.append(token)
            
            # Cache it
            if self.token_cache is not None:
                self.token_cache.put(cache_key, token)
        
        return tokens
    
    def get_stats(self) -> Dict[str, any]:
        """Get comprehensive index statistics."""
        redis_stats = self.redis_index.get_stats()
        
        stats = {
            'config': {
                'num_tables': self.config.num_tables,
                'bits_per_table': self.config.bits_per_table,
                'hash_length': self.config.hash_length,
                'buckets_per_table': self.config.buckets_per_table,
                'total_possible_buckets': self.config.total_buckets
            },
            'redis': redis_stats
        }
        
        if self.token_cache is not None:
            stats['cache'] = self.token_cache.stats()
        
        return stats
    
    def clear(self) -> bool:
        """Clear entire index (DESTRUCTIVE)."""
        logger.warning("Clearing entire LSH index!")
        
        count = self.redis_index.clear_all()
        
        if self.token_cache is not None:
            self.token_cache.clear()
        
        logger.warning(f"Cleared {count} keys from Redis index")
        return count >= 0
