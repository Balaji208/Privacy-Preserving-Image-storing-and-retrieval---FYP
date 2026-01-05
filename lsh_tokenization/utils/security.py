"""
Security Utilities
==================
Cryptographic utilities with HSM integration for secure key management.
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
    def load_key_from_hsm(
        key_label: str = "LSH_HMAC_MASTER_KEY",
        auto_initialize: bool = True
    ) -> bytes:
        """
        Load HMAC key from SoftHSM.
        
        Args:
            key_label: Label of key in HSM
            auto_initialize: If True, generate and store key if not exists
            
        Returns:
            32-byte HMAC key
            
        Raises:
            ValueError: If key not found and auto_initialize=False
            RuntimeError: If HSM is not available
        """
        try:
            from .hsm_key_manager import load_hmac_key_from_hsm, initialize_hmac_key_in_hsm
            
            try:
                # Try to load existing key
                return load_hmac_key_from_hsm(key_label)
            except ValueError:
                if auto_initialize:
                    logger.info("Key not found in HSM, initializing...")
                    return initialize_hmac_key_in_hsm()
                else:
                    raise
                    
        except ImportError:
            raise RuntimeError(
                "HSM modules not available. Install python-pkcs11 and configure SoftHSM."
            )
    
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
        """
        return hmac.compare_digest(a, b)
