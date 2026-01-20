"""
Redis Index Storage
===================

Thread-safe Redis-backed LSH index storage with FHE CT token support.
"""

from typing import List, Set, Optional
import logging
import redis
from redis.exceptions import RedisError
from ..config.lsh_config import LSHConfig

logger = logging.getLogger(__name__)


class RedisIndex:
    """
    Redis-backed LSH index with FHE CT HMAC token storage.
    
    Storage Schema:
        HMAC_Token (key) → List of HMAC(FHE_CT, image_id) (value)
    
    Example:
        "bucket_token_a3f5b2..." → [
            "fhe_ct_hmac_001",  # HMAC(FHE_CT1, img_001)
            "fhe_ct_hmac_002",  # HMAC(FHE_CT2, img_002)
            "fhe_ct_hmac_003"   # HMAC(FHE_CT3, img_003)
        ]
    
    Design:
        - Bucket token: HMAC(tenant_id:table_idx:bucket_id)
        - Value tokens: HMAC(FHE_CT, image_id)
        - Matches Azure Table storage PartitionKeys
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        config: LSHConfig,
        key_prefix: str = "lsh:token:"
    ):
        """
        Initialize Redis index.
        
        Args:
            redis_client: Connected Redis client
            config: LSH configuration
            key_prefix: Prefix for Redis keys (for namespacing)
        
        Raises:
            RedisError: If Redis connection fails
        """
        self.redis_client = redis_client
        self.config = config
        self.key_prefix = key_prefix
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info("Redis connection established")
        except RedisError as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    def _make_key(self, token: str) -> str:
        """Create Redis key from token."""
        return f"{self.key_prefix}{token}"
    
    def add_fhe_ct_token(
        self,
        bucket_token: str,
        fhe_ct_token: str
    ) -> bool:
        """
        Add FHE CT token to bucket.
        
        Args:
            bucket_token: HMAC token identifying the LSH bucket
            fhe_ct_token: HMAC(FHE_CT, image_id) to add
        
        Returns:
            True if added successfully
        """
        key = self._make_key(bucket_token)
        
        try:
            # Check bucket size limit
            if self.config.max_bucket_size is not None:
                current_size = self.redis_client.llen(key)
                if current_size >= self.config.max_bucket_size:
                    logger.warning(
                        f"Bucket {bucket_token[:16]}... at max size "
                        f"({self.config.max_bucket_size}), skipping"
                    )
                    return False
            
            # Atomic append
            self.redis_client.rpush(key, fhe_ct_token)
            
            # Set TTL if configured
            if self.config.redis_ttl is not None:
                self.redis_client.expire(key, self.config.redis_ttl)
            
            logger.debug(
                f"Added FHE CT token {fhe_ct_token[:16]}... "
                f"to bucket {bucket_token[:16]}..."
            )
            return True
            
        except RedisError as e:
            logger.error(f"Failed to add FHE CT token: {e}")
            return False
    
    def add_fhe_ct_tokens_batch(
        self,
        bucket_token: str,
        fhe_ct_tokens: List[str]
    ) -> int:
        """
        Add multiple FHE CT tokens to single bucket atomically.
        
        Args:
            bucket_token: HMAC token identifying the bucket
            fhe_ct_tokens: List of HMAC(FHE_CT, image_id) tokens
        
        Returns:
            Number of tokens successfully added
        """
        key = self._make_key(bucket_token)
        
        try:
            pipe = self.redis_client.pipeline()
            
            for fhe_ct_token in fhe_ct_tokens:
                pipe.rpush(key, fhe_ct_token)
            
            if self.config.redis_ttl is not None:
                pipe.expire(key, self.config.redis_ttl)
            
            pipe.execute()
            
            logger.debug(
                f"Added {len(fhe_ct_tokens)} FHE CT tokens "
                f"to bucket {bucket_token[:16]}..."
            )
            return len(fhe_ct_tokens)
            
        except RedisError as e:
            logger.error(f"Failed to add batch: {e}")
            return 0
    
    def get_fhe_ct_tokens(
        self,
        bucket_tokens: List[str],
        deduplicate: bool = True
    ) -> List[str]:
        """
        Retrieve FHE CT tokens from multiple buckets.
        
        Args:
            bucket_tokens: List of bucket HMAC tokens to query
            deduplicate: Remove duplicate FHE CT tokens
        
        Returns:
            List of FHE CT HMAC tokens (for Azure Table lookup)
        
        Example:
            >>> bucket_tokens = ["a3f5b2...", "d8c1e9..."]
            >>> fhe_ct_tokens = index.get_fhe_ct_tokens(bucket_tokens)
            >>> # Use tokens for Azure Table Storage lookup
            >>> for token in fhe_ct_tokens:
            ...     entity = azure_table.get_entity(partition_key=token)
        """
        all_fhe_ct_tokens = []
        
        try:
            pipe = self.redis_client.pipeline()
            
            for bucket_token in bucket_tokens:
                key = self._make_key(bucket_token)
                pipe.lrange(key, 0, -1)
            
            results = pipe.execute()
            
            # Collect and decode tokens
            for bucket_token, tokens_bytes in zip(bucket_tokens, results):
                if tokens_bytes:
                    tokens = [
                        t.decode('utf-8') if isinstance(t, bytes) else t
                        for t in tokens_bytes
                    ]
                    all_fhe_ct_tokens.extend(tokens)
            
            logger.debug(
                f"Retrieved {len(all_fhe_ct_tokens)} FHE CT tokens "
                f"from {len(bucket_tokens)} buckets"
            )
            
            # Deduplicate while preserving order
            if deduplicate:
                seen = set()
                unique_tokens = []
                for token in all_fhe_ct_tokens:
                    if token not in seen:
                        seen.add(token)
                        unique_tokens.append(token)
                
                logger.debug(
                    f"Deduplicated to {len(unique_tokens)} unique tokens"
                )
                return unique_tokens
            
            return all_fhe_ct_tokens
            
        except RedisError as e:
            logger.error(f"Failed to get FHE CT tokens: {e}")
            return []
    
    def get_bucket_size(self, token: str) -> int:
        """Get number of tokens in bucket."""
        key = self._make_key(token)
        try:
            return self.redis_client.llen(key)
        except RedisError as e:
            logger.error(f"Failed to get bucket size: {e}")
            return 0
    
    def remove_fhe_ct_token(
        self,
        bucket_token: str,
        fhe_ct_token: str
    ) -> int:
        """
        Remove FHE CT token from bucket.
        
        Returns:
            Number of occurrences removed
        """
        key = self._make_key(bucket_token)
        try:
            count = self.redis_client.lrem(key, 0, fhe_ct_token)
            if count > 0:
                logger.debug(
                    f"Removed {count} occurrence(s) of token "
                    f"{fhe_ct_token[:16]}..."
                )
            return count
        except RedisError as e:
            logger.error(f"Failed to remove token: {e}")
            return 0
    
    def delete_bucket(self, bucket_token: str) -> bool:
        """Delete entire bucket."""
        key = self._make_key(bucket_token)
        try:
            result = self.redis_client.delete(key)
            logger.info(f"Deleted bucket {bucket_token[:16]}...")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to delete bucket: {e}")
            return False
    
    def get_all_buckets(self) -> Set[str]:
        """Get all bucket tokens in the index."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            tokens = {
                key.decode('utf-8').replace(self.key_prefix, '')
                for key in keys
            }
            
            logger.info(f"Found {len(tokens)} buckets in index")
            return tokens
        except RedisError as e:
            logger.error(f"Failed to get buckets: {e}")
            return set()
    
    def clear_all(self) -> int:
        """
        Clear entire index (DESTRUCTIVE).
        
        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                count = self.redis_client.delete(*keys)
                logger.warning(f"Cleared {count} keys from index")
                return count
            return 0
        except RedisError as e:
            logger.error(f"Failed to clear index: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """Get index statistics."""
        try:
            buckets = self.get_all_buckets()
            
            if not buckets:
                return {
                    'num_buckets': 0,
                    'total_tokens': 0,
                    'avg_bucket_size': 0.0,
                    'max_bucket_size': 0,
                    'min_bucket_size': 0
                }
            
            sizes = []
            total_tokens = 0
            
            for bucket_token in buckets:
                size = self.get_bucket_size(bucket_token)
                sizes.append(size)
                total_tokens += size
            
            return {
                'num_buckets': len(buckets),
                'total_tokens': total_tokens,
                'avg_bucket_size': total_tokens / len(buckets),
                'max_bucket_size': max(sizes) if sizes else 0,
                'min_bucket_size': min(sizes) if sizes else 0
            }
        except RedisError as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
