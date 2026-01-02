"""
LSH Tokenization Module
========================
Production-ready LSH bucketization with HMAC-SHA3-256 tokenization for Redis storage.

This module provides privacy-preserving locality-sensitive hashing (LSH) indexing
for binary hash codes with secure bucket tokenization and Redis-backed storage.

Author: Applied Cryptography Research Team
Version: 1.0.0
License: MIT
"""

from .pipeline.index_builder import LSHIndexer
from .config.lsh_config import LSHConfig
from .simhash.simhash_generator import SimHashGenerator
from .tokenization.hmac_tokenizer import HMACTokenizer
from .storage.redis_index import RedisIndex
from .metrics.collision_metrics import CollisionMetrics

__version__ = "1.0.0"
__all__ = [
    "LSHIndexer",
    "LSHConfig",
    "SimHashGenerator",
    "HMACTokenizer",
    "RedisIndex",
    "CollisionMetrics",
]
