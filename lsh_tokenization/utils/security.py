"""
Security Utilities
==================
Cryptographic utilities for secure key management and operations.
"""

import os
import secrets
import hmac
import hashlib
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Security utilities for key management and cryptographic operations."""
    
    # Required key lengths
    HMAC_KEY_LENGTH = 32  # 256 bits for HMAC-SHA3-256
    
    @staticmethod
    def generate_hmac_key() -> bytes:
        """
        Generate cryptographically secure HMAC key.
        
        Returns:
            32-byte random key suitable for HMAC-SHA3-256
            
        Security:
            Uses secrets module (CSPRNG)
        """
        key = secrets.token_bytes(SecurityUtils.HMAC_KEY_LENGTH)
        logger.info(f"Generated new HMAC key ({len(key)} bytes)")
        return key
    
    @staticmethod
    def load_key_from_env(env_var: str = "LSH_HMAC_KEY") -> Optional[bytes]:
        """
        Load HMAC key from environment variable.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            Key bytes if found, None otherwise
            
        Raises:
            ValueError: If key format is invalid
        """
        key_hex = os.environ.get(env_var)
        
        if key_hex is None:
            logger.warning(f"Environment variable {env_var} not found")
            return None
        
        try:
            key_bytes = bytes.fromhex(key_hex)
        except ValueError as e:
            raise ValueError(
                f"Invalid hex format in {env_var}: {e}"
            ) from e
        
        if len(key_bytes) != SecurityUtils.HMAC_KEY_LENGTH:
            raise ValueError(
                f"Key must be {SecurityUtils.HMAC_KEY_LENGTH} bytes, "
                f"got {len(key_bytes)}"
            )
        
        logger.info(f"Loaded HMAC key from environment ({len(key_bytes)} bytes)")
        return key_bytes
    
    @staticmethod
    def validate_key(key: bytes) -> None:
        """
        Validate HMAC key format.
        
        Args:
            key: Key to validate
            
        Raises:
            ValueError: If key is invalid
        """
        if not isinstance(key, bytes):
            raise ValueError(f"Key must be bytes, got {type(key)}")
        
        if len(key) != SecurityUtils.HMAC_KEY_LENGTH:
            raise ValueError(
                f"Key must be {SecurityUtils.HMAC_KEY_LENGTH} bytes, "
                f"got {len(key)}"
            )
    
    @staticmethod
    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """
        Constant-time comparison to prevent timing attacks.
        
        Args:
            a: First byte string
            b: Second byte string
            
        Returns:
            True if equal, False otherwise
            
        Security:
            Uses hmac.compare_digest for constant-time comparison
        """
        return hmac.compare_digest(a, b)
    
    @staticmethod
    def secure_zero(data: bytearray) -> None:
        """
        Securely zero out sensitive data in memory.
        
        Args:
            data: Bytearray to zero out
            
        Note:
            Best-effort memory clearing. Python's GC may still leave copies.
        """
        if isinstance(data, bytearray):
            for i in range(len(data)):
                data[i] = 0
    
    @staticmethod
    def derive_key(master_key: bytes, context: bytes, length: int = 32) -> bytes:
        """
        Derive sub-key from master key using HKDF-like construction.
        
        Args:
            master_key: Master key
            context: Context information for key derivation
            length: Output length in bytes
            
        Returns:
            Derived key
            
        Security:
            Uses HMAC-SHA3-256 for key derivation
        """
        h = hashlib.sha3_256()
        h.update(master_key)
        h.update(context)
        derived = h.digest()
        
        if length > len(derived):
            # Extend if needed
            additional = hashlib.sha3_256(derived + master_key).digest()
            derived = derived + additional
        
        return derived[:length]
