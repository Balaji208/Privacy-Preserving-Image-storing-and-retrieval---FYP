"""
Redis Client
============

Synchronous Redis client for LSH token storage.
"""

import logging
from typing import Set, Optional, List
import redis

from config.settings import Settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client for LSH candidate collection.
    
    Uses synchronous redis-py client.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize Redis client.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.client: Optional[redis.Redis] = None
        
        logger.info("Initializing Redis client...")
    
    def connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                ssl=self.settings.redis_ssl,
                max_connections=self.settings.redis_max_connections,
                socket_timeout=self.settings.redis_socket_timeout,
                decode_responses=False  # Keep bytes for hash indices
            )
            
            # Test connection
            self.client.ping()
            
            logger.info(
                f"✓ Redis connected: {self.settings.redis_host}:"
                f"{self.settings.redis_port}"
            )
            
        except redis.ConnectionError as e:
            logger.error(f"✗ Redis connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ Redis initialization error: {e}")
            raise
    
    def disconnect(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
            logger.info("✓ Redis disconnected")
    
    def get_members(self, key: str) -> Set[bytes]:
        """
        Get all members of a Redis set.
        
        Args:
            key: Redis set key (LSH token)
        
        Returns:
            Set of hash indices (as bytes)
        """
        try:
            if not self.client:
                raise RuntimeError("Redis client not connected")
            
            members = self.client.smembers(key)
            return members if members else set()
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting members for key {key}: {e}")
            return set()
    
    def get_members_batch(self, keys: List[str]) -> List[Set[bytes]]:
        """
        Get members for multiple keys in batch.
        
        Args:
            keys: List of Redis set keys
        
        Returns:
            List of sets (one per key)
        """
        try:
            if not self.client:
                raise RuntimeError("Redis client not connected")
            
            # Use pipeline for batch operations
            with self.client.pipeline() as pipe:
                for key in keys:
                    pipe.smembers(key)
                results = pipe.execute()
            
            return [result if result else set() for result in results]
            
        except redis.RedisError as e:
            logger.error(f"Redis batch operation error: {e}")
            return [set() for _ in keys]
    
    def set_add(self, key: str, *values: bytes):
        """
        Add members to a Redis set.
        
        Args:
            key: Redis set key
            values: Values to add
        """
        try:
            if not self.client:
                raise RuntimeError("Redis client not connected")
            
            if values:
                self.client.sadd(key, *values)
                logger.debug(f"Added {len(values)} members to {key}")
                
        except redis.RedisError as e:
            logger.error(f"Redis error adding to set {key}: {e}")
    
    def key_exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Redis key
        
        Returns:
            True if key exists
        """
        try:
            if not self.client:
                return False
            
            return self.client.exists(key) > 0
            
        except redis.RedisError:
            return False
    
    def get_set_size(self, key: str) -> int:
        """
        Get size of a Redis set.
        
        Args:
            key: Redis set key
        
        Returns:
            Number of members in set
        """
        try:
            if not self.client:
                return 0
            
            return self.client.scard(key)
            
        except redis.RedisError:
            return 0
    
    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if connected
        """
        try:
            if not self.client:
                return False
            
            return self.client.ping()
            
        except redis.RedisError:
            return False
    
    def get_info(self) -> dict:
        """
        Get Redis server info.
        
        Returns:
            Redis server information
        """
        try:
            if not self.client:
                return {}
            
            info = self.client.info()
            return {
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self.client.dbsize()
            }
            
        except redis.RedisError as e:
            logger.error(f"Error getting Redis info: {e}")
            return {}


def get_redis_client(settings: Settings) -> RedisClient:
    """
    Factory function to create and connect Redis client.
    
    Args:
        settings: Application settings
    
    Returns:
        Connected RedisClient instance
    """
    client = RedisClient(settings)
    client.connect()
    return client
