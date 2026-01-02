"""
LSH Index Builder Pipeline
===========================
Main pipeline orchestrating LSH bucketing, tokenization, and storage.
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

logger = logging.getLogger(__name__)


class LSHIndexer:
    """
    Complete LSH indexing pipeline with simplified storage.
    
    Orchestrates:
        1. SimHash bucket generation
        2. HMAC tokenization
        3. Redis storage (TOKEN → [hash_id, hash_id, ...])
    
    This is the main API for the module.
    
    Attributes:
        redis_index: Redis storage backend
        tokenizer: HMAC tokenizer
        simhash_generator: SimHash generator
        config: LSH configuration
        token_cache: Optional token cache
    
    Example:
        >>> import redis
        >>> from lsh_tokenization import LSHIndexer, LSHConfig
        >>> 
        >>> # Setup
        >>> redis_client = redis.Redis(host='localhost', port=6379, db=0)
        >>> config = LSHConfig()
        >>> hmac_key = b'...'  # 32-byte key
        >>> 
        >>> # Initialize
        >>> indexer = LSHIndexer(redis_client, hmac_key, config)
        >>> 
        >>> # Add image hash
        >>> binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        >>> indexer.add(binary_hash, "tenant_1", "hash_abc123")
        >>> 
        >>> # Query
        >>> candidates = indexer.query(binary_hash, "tenant_1")
        >>> print(candidates)  # ['hash_abc123', 'hash_xyz789', ...]
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
        Initialize LSH indexer.
        
        Args:
            redis_client: Connected Redis client
            hmac_key: 256-bit HMAC master key
            config: LSH configuration (default: LSHConfig())
            use_token_cache: Enable token caching for performance
            token_cache_size: Maximum cached tokens
            
        Raises:
            ValueError: If configuration is invalid
            redis.RedisError: If Redis connection fails
        """
        # Initialize configuration
        self.config = config or LSHConfig()
        
        # Initialize components
        self.simhash_generator = SimHashGenerator(self.config)
        self.tokenizer = HMACTokenizer(hmac_key)
        self.redis_index = RedisIndex(redis_client, self.config)
        
        # Optional token cache
        self.token_cache = None
        if use_token_cache:
            self.token_cache = TokenCache(max_size=token_cache_size)
        
        logger.info(
            f"Initialized LSH indexer: L={self.config.num_tables}, "
            f"K={self.config.bits_per_table}, cache={use_token_cache}"
        )
    
    def add(
        self,
        binary_hash: np.ndarray,
        tenant_id: str,
        hash_id: str
    ) -> bool:
        """
        Add binary hash to the index.
        
        This is the main indexing operation. It:
            1. Generates L bucket IDs using SimHash
            2. Tokenizes each (tenant_id, bucket_id) pair
            3. Stores hash_id under each token in Redis
        
        Args:
            binary_hash: Binary hash (256 bits as numpy array)
            tenant_id: Tenant identifier for multi-tenancy
            hash_id: Hash identifier to store
            
        Returns:
            True if successfully added to all buckets, False otherwise
            
        Raises:
            ValueError: If binary_hash format is invalid
            
        Storage Result:
            HMAC_Token_1 → [..., hash_id]
            HMAC_Token_2 → [..., hash_id]
            ...
            HMAC_Token_6 → [..., hash_id]
            
        Example:
            >>> binary_hash = np.array([1, 0, 1, ...], dtype=np.uint8)  # 256 bits
            >>> success = indexer.add(
            ...     binary_hash,
            ...     tenant_id="acme_corp",
            ...     hash_id="hash_abc123"
            ... )
        """
        # Validate input
        BitUtils.validate_binary_hash(binary_hash, self.config.hash_length)
        
        try:
            # Step 1: Generate LSH bucket IDs
            bucket_ids = self.simhash_generator.generate_bucket_ids(binary_hash)
            
            logger.debug(
                f"Generated {len(bucket_ids)} bucket IDs for hash_id={hash_id}"
            )
            
            # Step 2: Tokenize bucket IDs
            tokens = self._get_tokens(tenant_id, bucket_ids)
            
            # Step 3: Store hash_id in Redis under each token
            success_count = 0
            for token in tokens:
                success = self.redis_index.add_hash_id(
                    token=token,
                    hash_id=hash_id
                )
                if success:
                    success_count += 1
            
            logger.info(
                f"Added hash_id={hash_id} to {success_count}/{len(tokens)} buckets "
                f"(tenant={tenant_id})"
            )
            
            return success_count == len(tokens)
            
        except Exception as e:
            logger.error(f"Failed to add hash to index: {e}")
            return False
    
    def add_batch(
        self,
        entries: List[Dict[str, any]]
    ) -> Dict[str, int]:
        """
        Add multiple hashes efficiently.
        
        Args:
            entries: List of dictionaries with keys:
                - binary_hash: np.ndarray
                - tenant_id: str
                - hash_id: str
                
        Returns:
            Dictionary with statistics:
                - total: Total entries
                - success: Successfully added
                - failed: Failed entries
                
        Example:
            >>> entries = [
            ...     {
            ...         "binary_hash": hash1,
            ...         "tenant_id": "tenant_1",
            ...         "hash_id": "hash_001"
            ...     },
            ...     {
            ...         "binary_hash": hash2,
            ...         "tenant_id": "tenant_1",
            ...         "hash_id": "hash_002"
            ...     }
            ... ]
            >>> stats = indexer.add_batch(entries)
        """
        total = len(entries)
        success = 0
        failed = 0
        
        for entry in entries:
            result = self.add(
                binary_hash=entry['binary_hash'],
                tenant_id=entry['tenant_id'],
                hash_id=entry['hash_id']
            )
            
            if result:
                success += 1
            else:
                failed += 1
        
        logger.info(
            f"Batch add complete: {success}/{total} successful, {failed} failed"
        )
        
        return {
            'total': total,
            'success': success,
            'failed': failed
        }
    
    def query(
        self,
        binary_hash: np.ndarray,
        tenant_id: str,
        deduplicate: bool = True
    ) -> List[str]:
        """
        Query the index for candidate hash_ids.
        
        Args:
            binary_hash: Query binary hash (256 bits)
            tenant_id: Tenant identifier
            deduplicate: Remove duplicate hash_ids
            
        Returns:
            List of candidate hash_ids
            
        Example:
            >>> query_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
            >>> candidates = indexer.query(query_hash, "tenant_1")
            >>> print(candidates)
            ['hash_001', 'hash_003', 'hash_007', ...]
        """
        # Validate input
        BitUtils.validate_binary_hash(binary_hash, self.config.hash_length)
        
        try:
            # Step 1: Generate bucket IDs
            bucket_ids = self.simhash_generator.generate_bucket_ids(binary_hash)
            
            # Step 2: Get tokens
            tokens = self._get_tokens(tenant_id, bucket_ids)
            
            # Step 3: Retrieve hash_ids from Redis
            hash_ids = self.redis_index.get_hash_ids(
                tokens=tokens,
                deduplicate=deduplicate
            )
            
            logger.info(
                f"Query returned {len(hash_ids)} candidate hash_ids from "
                f"{len(tokens)} tokens (tenant={tenant_id})"
            )
            
            return hash_ids
            
        except Exception as e:
            logger.error(f"Failed to query index: {e}")
            return []
    
    def _get_tokens(
        self,
        tenant_id: str,
        bucket_ids: List[int]
    ) -> List[str]:
        """
        Get tokens for bucket IDs (with optional caching).
        
        Args:
            tenant_id: Tenant identifier
            bucket_ids: List of bucket IDs
            
        Returns:
            List of HMAC tokens
        """
        tokens = []
        
        for table_idx, bucket_id in enumerate(bucket_ids):
            # Check cache first
            if self.token_cache is not None:
                cache_key = (tenant_id, bucket_id, table_idx)
                cached_token = self.token_cache.get(cache_key)
                
                if cached_token is not None:
                    tokens.append(cached_token)
                    continue
            
            # Compute token
            token = self.tokenizer.tokenize(tenant_id, bucket_id, table_idx)
            tokens.append(token)
            
            # Cache it
            if self.token_cache is not None:
                self.token_cache.put(cache_key, token)
        
        return tokens
    
    def delete_hash(
        self,
        binary_hash: np.ndarray,
        tenant_id: str,
        hash_id: str
    ) -> int:
        """
        Remove hash_id from all its buckets.
        
        Args:
            binary_hash: Binary hash of item
            tenant_id: Tenant identifier
            hash_id: Hash ID to remove
            
        Returns:
            Total number of occurrences removed across all buckets
        """
        # Generate tokens
        bucket_ids = self.simhash_generator.generate_bucket_ids(binary_hash)
        tokens = self._get_tokens(tenant_id, bucket_ids)
        
        total_removed = 0
        
        for token in tokens:
            count = self.redis_index.remove_hash_id(token, hash_id)
            total_removed += count
        
        logger.info(
            f"Removed hash_id={hash_id} ({total_removed} total occurrences) "
            f"from {len(tokens)} buckets"
        )
        
        return total_removed
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get comprehensive index statistics.
        
        Returns:
            Dictionary with statistics about the index
        """
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
        
        # Add cache stats if available
        if self.token_cache is not None:
            stats['cache'] = self.token_cache.stats()
        
        return stats
    
    def clear(self) -> bool:
        """
        Clear entire index (WARNING: destructive).
        
        Returns:
            True if cleared successfully
        """
        logger.warning("Clearing entire LSH index!")
        
        count = self.redis_index.clear_all()
        
        if self.token_cache is not None:
            self.token_cache.clear()
        
        logger.warning(f"Cleared {count} keys from Redis index")
        
        return count >= 0
