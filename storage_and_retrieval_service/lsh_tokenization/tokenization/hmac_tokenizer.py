"""
HMAC-SHA3-256 Tokenizer
=======================
Generates cryptographic tokens from bucket IDs for privacy-preserving storage.
"""

import hashlib
import hmac
from typing import List
import logging

from ..utils.security import SecurityUtils

logger = logging.getLogger(__name__)


class HMACTokenizer:
    """
    HMAC-SHA3-256 based bucket tokenizer.
    
    Converts (tenant_id, bucket_id) pairs into deterministic tokens that:
    - Hide bucket semantics from storage layer
    - Are collision-resistant
    - Are post-quantum safe (hash-based)
    - Support multi-tenancy
    
    Attributes:
        master_key: 256-bit HMAC key
    
    Security Properties:
        - Tokens are deterministic for reproducibility
        - Tokens reveal no information about bucket structure
        - Tokens are computationally infeasible to reverse
        - Key separation between tenants via HMAC input
    """
    
    def __init__(self, master_key: bytes):
        """
        Initialize HMAC tokenizer.
        
        Args:
            master_key: 256-bit master key for HMAC
            
        Raises:
            ValueError: If master_key is invalid
        """
        SecurityUtils.validate_key(master_key)
        self._master_key = master_key
        
        logger.info("Initialized HMAC tokenizer (SHA3-256)")
    
    def tokenize(self, tenant_id: str, bucket_id: int, table_idx: int) -> str:
        """
        Generate token for (tenant_id, bucket_id, table_idx) triple.
        
        Args:
            tenant_id: Tenant identifier
            bucket_id: LSH bucket ID
            table_idx: LSH table index
            
        Returns:
            Hex-encoded token (64 characters = 32 bytes)
            
        Token Format:
            token = HMAC-SHA3-256(
                master_key,
                tenant_id || ":" || table_idx || ":" || bucket_id
            )
            
        Example:
            >>> tokenizer = HMACTokenizer(master_key)
            >>> token = tokenizer.tokenize("tenant_abc", 1234, 0)
            >>> len(token)
            64  # 32 bytes in hex
        """
        # Construct message: tenant_id:table_idx:bucket_id
        message = f"{tenant_id}:{table_idx}:{bucket_id}"
        message_bytes = message.encode('utf-8')
        
        # Compute HMAC-SHA3-256
        h = hmac.new(
            self._master_key,
            message_bytes,
            hashlib.sha3_256
        )
        
        # Return hex-encoded token
        token = h.hexdigest()
        
        logger.debug(
            f"Generated token for tenant={tenant_id}, table={table_idx}, "
            f"bucket={bucket_id}: {token[:16]}..."
        )
        
        return token
    
    def tokenize_batch(
        self,
        tenant_id: str,
        bucket_ids: List[int]
    ) -> List[str]:
        """
        Generate tokens for multiple bucket IDs.
        
        Args:
            tenant_id: Tenant identifier
            bucket_ids: List of L bucket IDs from LSH tables
            
        Returns:
            List of L tokens (one per table)
        """
        tokens = [
            self.tokenize(tenant_id, bucket_id, table_idx)
            for table_idx, bucket_id in enumerate(bucket_ids)
        ]
        
        logger.debug(
            f"Generated {len(tokens)} tokens for tenant={tenant_id}"
        )
        
        return tokens
    
    def verify_token(
        self,
        token: str,
        tenant_id: str,
        bucket_id: int,
        table_idx: int
    ) -> bool:
        """
        Verify token matches expected value (constant-time comparison).
        
        Args:
            token: Token to verify
            tenant_id: Expected tenant ID
            bucket_id: Expected bucket ID
            table_idx: Expected table index
            
        Returns:
            True if token is valid, False otherwise
            
        Security:
            Uses constant-time comparison to prevent timing attacks
        """
        expected_token = self.tokenize(tenant_id, bucket_id, table_idx)
        
        # Constant-time comparison
        return SecurityUtils.constant_time_compare(
            token.encode('utf-8'),
            expected_token.encode('utf-8')
        )
    
    def get_token_info(self, token: str) -> dict:
        """
        Get metadata about a token (for debugging).
        
        Args:
            token: Token hex string
            
        Returns:
            Dictionary with token metadata
            
        Note:
            This does NOT reverse the token - only provides format info
        """
        return {
            'length_hex': len(token),
            'length_bytes': len(token) // 2,
            'algorithm': 'HMAC-SHA3-256',
            'reversible': False
        }


class TokenCache:
    """
    Optional in-memory token cache for performance.
    
    Caches recently computed tokens to avoid redundant HMAC operations.
    Thread-safe with LRU eviction.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize token cache.
        
        Args:
            max_size: Maximum number of cached tokens
        """
        from collections import OrderedDict
        import threading
        
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        
        logger.info(f"Initialized token cache (max_size={max_size})")
    
    def get(self, key: tuple) -> str:
        """
        Get cached token.
        
        Args:
            key: (tenant_id, bucket_id, table_idx) tuple
            
        Returns:
            Cached token or None if not found
        """
        with self._lock:
            if key in self._cache:
                # Move to end (LRU)
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def put(self, key: tuple, token: str) -> None:
        """
        Cache token.
        
        Args:
            key: (tenant_id, bucket_id, table_idx) tuple
            token: Token to cache
        """
        with self._lock:
            if key in self._cache:
                # Update and move to end
                self._cache.move_to_end(key)
            else:
                # Add new entry
                self._cache[key] = token
                
                # Evict oldest if over capacity
                if len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear all cached tokens."""
        with self._lock:
            self._cache.clear()
            logger.info("Token cache cleared")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'utilization': len(self._cache) / self.max_size
            }
