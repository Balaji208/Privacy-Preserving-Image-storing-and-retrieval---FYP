"""
LSH Configuration Module
========================
Centralized configuration for LSH parameters.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LSHConfig:
    """
    Immutable LSH configuration.
    
    Attributes:
        hash_length: Length of input binary hash (default: 256 bits)
        num_tables: Number of LSH tables/hash functions (L) (default: 6)
        bits_per_table: Number of bits per table (K) (default: 12)
        random_seed: Seed for reproducible random projections (default: 42)
        redis_ttl: TTL for Redis keys in seconds (None = no expiry)
        max_bucket_size: Maximum entries per bucket (None = unlimited)
    
    Design Rationale:
        - L=6, K=12: Balance between recall and candidate reduction
        - 12-bit buckets = 4096 possible buckets per table
        - 6 tables provide redundancy for similar items
    """
    
    hash_length: int = 256
    num_tables: int = 6
    bits_per_table: int = 12
    random_seed: int = 42
    redis_ttl: Optional[int] = None
    max_bucket_size: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration parameters."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate configuration constraints.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if self.hash_length <= 0:
            raise ValueError(f"hash_length must be positive, got {self.hash_length}")
        
        if self.num_tables <= 0:
            raise ValueError(f"num_tables must be positive, got {self.num_tables}")
        
        if self.bits_per_table <= 0:
            raise ValueError(f"bits_per_table must be positive, got {self.bits_per_table}")
        
        if self.bits_per_table > self.hash_length:
            raise ValueError(
                f"bits_per_table ({self.bits_per_table}) cannot exceed "
                f"hash_length ({self.hash_length})"
            )
        
        if self.redis_ttl is not None and self.redis_ttl <= 0:
            raise ValueError(f"redis_ttl must be positive or None, got {self.redis_ttl}")
        
        if self.max_bucket_size is not None and self.max_bucket_size <= 0:
            raise ValueError(
                f"max_bucket_size must be positive or None, got {self.max_bucket_size}"
            )
        
        logger.info(
            f"LSH Configuration validated: L={self.num_tables}, K={self.bits_per_table}, "
            f"hash_length={self.hash_length}"
        )
    
    @property
    def total_bits_used(self) -> int:
        """Total bits used across all tables."""
        return self.num_tables * self.bits_per_table
    
    @property
    def buckets_per_table(self) -> int:
        """Number of possible buckets per table."""
        return 2 ** self.bits_per_table
    
    @property
    def total_buckets(self) -> int:
        """Total number of buckets across all tables."""
        return self.num_tables * self.buckets_per_table
