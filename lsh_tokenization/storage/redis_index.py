"""
Redis Index Storage
===================
Thread-safe Redis-backed LSH index storage with simplified schema.
"""

from typing import List, Set, Optional
import logging
import redis
from redis.exceptions import RedisError

from ..config.lsh_config import LSHConfig

logger = logging.getLogger(__name__)


class RedisIndex:
    """
    Redis-backed LSH index with simplified storage.
    
    Storage Schema:
        HMAC_Token (key) → List of hash_ids (value)
        
        Example:
            "a3f5b2..." → ["hash_001", "hash_002", "hash_003"]
            "d8c1e9..." → ["hash_004", "hash_001", "hash_005"]
    
    Design:
        - Uses Redis Lists for efficient append operations
        - Each token maps directly to list of hash IDs
        - Supports atomic operations via Redis commands
        - Handles concurrent writes safely
        - Optional TTL for automatic cleanup
    
    Attributes:
        redis_client: Redis connection
        config: LSH configuration
        key_prefix: Prefix for all Redis keys
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
        """
        Create Redis key from token.
        
        Args:
            token: Token hex string
            
        Returns:
            Full Redis key with prefix
        """
        return f"{self.key_prefix}{token}"
    
    def add_hash_id(
        self,
        token: str,
        hash_id: str
    ) -> bool:
        """
        Add hash_id to token's bucket.
        
        Args:
            token: HMAC token identifying the bucket
            hash_id: Hash identifier to add
            
        Returns:
            True if added successfully, False otherwise
            
        Thread-Safety:
            Uses Redis RPUSH which is atomic
            
        Example:
            >>> index.add_hash_id("a3f5b2c1...", "hash_12345")
            True
        """
        key = self._make_key(token)
        
        try:
            # Check bucket size limit
            if self.config.max_bucket_size is not None:
                current_size = self.redis_client.llen(key)
                if current_size >= self.config.max_bucket_size:
                    logger.warning(
                        f"Bucket {token[:16]}... at max size "
                        f"({self.config.max_bucket_size}), skipping add"
                    )
                    return False
            
            # Atomic append
            self.redis_client.rpush(key, hash_id)
            
            # Set TTL if configured
            if self.config.redis_ttl is not None:
                self.redis_client.expire(key, self.config.redis_ttl)
            
            logger.debug(
                f"Added hash_id={hash_id} to token {token[:16]}..."
            )
            
            return True
            
        except RedisError as e:
            logger.error(f"Failed to add hash_id: {e}")
            return False
    
    def add_hash_id_batch(
        self,
        token: str,
        hash_ids: List[str]
    ) -> int:
        """
        Add multiple hash_ids to single token atomically.
        
        Args:
            token: HMAC token identifying the bucket
            hash_ids: List of hash IDs to add
            
        Returns:
            Number of hash_ids successfully added
        """
        key = self._make_key(token)
        
        try:
            # Use pipeline for atomic batch operation
            pipe = self.redis_client.pipeline()
            
            for hash_id in hash_ids:
                pipe.rpush(key, hash_id)
            
            # Set TTL if configured
            if self.config.redis_ttl is not None:
                pipe.expire(key, self.config.redis_ttl)
            
            # Execute atomically
            pipe.execute()
            
            logger.debug(
                f"Added {len(hash_ids)} hash_ids to token {token[:16]}..."
            )
            
            return len(hash_ids)
            
        except RedisError as e:
            logger.error(f"Failed to add batch: {e}")
            return 0
    
    def get_hash_ids(
        self,
        tokens: List[str],
        deduplicate: bool = True
    ) -> List[str]:
        """
        Retrieve hash_ids from multiple tokens.
        
        Args:
            tokens: List of HMAC tokens to query
            deduplicate: Remove duplicate hash_ids
            
        Returns:
            List of hash_ids (unique if deduplicate=True)
            
        Example:
            >>> tokens = ["a3f5b2...", "d8c1e9..."]
            >>> hash_ids = index.get_hash_ids(tokens)
            >>> print(hash_ids)
            ['hash_001', 'hash_002', 'hash_003', 'hash_004']
        """
        all_hash_ids = []
        
        try:
            # Use pipeline for efficient batch retrieval
            pipe = self.redis_client.pipeline()
            
            for token in tokens:
                key = self._make_key(token)
                pipe.lrange(key, 0, -1)  # Get all hash_ids
            
            results = pipe.execute()
            
            # Collect hash_ids
            for token, hash_ids_bytes in zip(tokens, results):
                if hash_ids_bytes:
                    # Decode bytes to strings
                    hash_ids = [
                        hid.decode('utf-8') if isinstance(hid, bytes) else hid
                        for hid in hash_ids_bytes
                    ]
                    all_hash_ids.extend(hash_ids)
            
            logger.debug(
                f"Retrieved {len(all_hash_ids)} hash_ids from "
                f"{len(tokens)} tokens"
            )
            
            # Deduplicate while preserving order
            if deduplicate:
                seen = set()
                unique_hash_ids = []
                for hash_id in all_hash_ids:
                    if hash_id not in seen:
                        seen.add(hash_id)
                        unique_hash_ids.append(hash_id)
                
                logger.debug(
                    f"Deduplicated to {len(unique_hash_ids)} unique hash_ids"
                )
                return unique_hash_ids
            
            return all_hash_ids
            
        except RedisError as e:
            logger.error(f"Failed to get hash_ids: {e}")
            return []
    
    def get_bucket_size(self, token: str) -> int:
        """
        Get number of hash_ids in bucket.
        
        Args:
            token: HMAC token identifying the bucket
            
        Returns:
            Number of hash_ids in bucket
        """
        key = self._make_key(token)
        
        try:
            return self.redis_client.llen(key)
        except RedisError as e:
            logger.error(f"Failed to get bucket size: {e}")
            return 0
    
    def remove_hash_id(
        self,
        token: str,
        hash_id: str
    ) -> int:
        """
        Remove hash_id from bucket.
        
        Args:
            token: HMAC token
            hash_id: Hash ID to remove
            
        Returns:
            Number of occurrences removed
            
        Note:
            Uses LREM which removes all occurrences
        """
        key = self._make_key(token)
        
        try:
            # Remove all occurrences
            count = self.redis_client.lrem(key, 0, hash_id)
            
            if count > 0:
                logger.debug(
                    f"Removed {count} occurrence(s) of hash_id={hash_id} "
                    f"from token {token[:16]}..."
                )
            
            return count
            
        except RedisError as e:
            logger.error(f"Failed to remove hash_id: {e}")
            return 0
    
    def delete_token(self, token: str) -> bool:
        """
        Delete entire bucket for a token.
        
        Args:
            token: Token to delete
            
        Returns:
            True if deleted, False otherwise
        """
        key = self._make_key(token)
        
        try:
            result = self.redis_client.delete(key)
            logger.info(f"Deleted token {token[:16]}...")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to delete token: {e}")
            return False
    
    def get_all_tokens(self) -> Set[str]:
        """
        Get all tokens in the index.
        
        Returns:
            Set of token strings
            
        Warning:
            Expensive operation - use sparingly
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            # Extract tokens from keys
            tokens = {
                key.decode('utf-8').replace(self.key_prefix, '')
                for key in keys
            }
            
            logger.info(f"Found {len(tokens)} tokens in index")
            return tokens
            
        except RedisError as e:
            logger.error(f"Failed to get tokens: {e}")
            return set()
    
    def clear_all(self) -> int:
        """
        Clear entire index.
        
        Returns:
            Number of keys deleted
            
        Warning:
            Destructive operation - use with caution
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
        """
        Get index statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            tokens = self.get_all_tokens()
            
            if not tokens:
                return {
                    'num_tokens': 0,
                    'total_hash_ids': 0,
                    'avg_bucket_size': 0.0,
                    'max_bucket_size': 0,
                    'min_bucket_size': 0
                }
            
            # Get sizes for all buckets
            sizes = []
            total_hash_ids = 0
            
            for token in tokens:
                size = self.get_bucket_size(token)
                sizes.append(size)
                total_hash_ids += size
            
            return {
                'num_tokens': len(tokens),
                'total_hash_ids': total_hash_ids,
                'avg_bucket_size': total_hash_ids / len(tokens),
                'max_bucket_size': max(sizes) if sizes else 0,
                'min_bucket_size': min(sizes) if sizes else 0
            }
            
        except RedisError as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
