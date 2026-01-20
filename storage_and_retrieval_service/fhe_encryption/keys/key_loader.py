"""
BFV Key Loader with SoftHSM Integration
========================================
Securely loads BFV keys from SoftHSM.

Key Labels in HSM:
    - BFV_PUBLIC_KEY: Public encryption key
    - BFV_SECRET_KEY: Secret decryption key (sensitive)
    - BFV_RELIN_KEY: Relinearization key
    - BFV_GALOIS_KEY: Galois rotation keys

Security Architecture:
    - Keys never generated in this module
    - Keys loaded on-demand from HSM
    - Secret key usage minimized
    - Keys cached in memory with secure zeroization
"""

from typing import Optional, Tuple
import logging
from threading import Lock

logger = logging.getLogger(__name__)

# Import HSM modules
try:
    from hsm.hsm_manager import get_hsm_manager
    HSM_AVAILABLE = True
except ImportError:
    HSM_AVAILABLE = False
    logger.warning("HSM modules not available")


class BFVKeyLoader:
    """
    Loads BFV keys from SoftHSM.
    
    Thread-safe key loading with caching for performance.
    
    Key Lifecycle:
        1. Keys generated externally (offline)
        2. Keys stored in SoftHSM
        3. This loader retrieves keys on-demand
        4. Keys cached in memory
        5. Cache zeroized on cleanup
    
    Attributes:
        hsm: HSM manager instance
        _cache: In-memory key cache
        _lock: Thread lock for cache access
    """
    
    # Standard key labels
    PUBLIC_KEY_LABEL = "BFV_PUBLIC_KEY"
    SECRET_KEY_LABEL = "BFV_SECRET_KEY"
    RELIN_KEY_LABEL = "BFV_RELIN_KEY"
    GALOIS_KEY_LABEL = "BFV_GALOIS_KEY"
    
    def __init__(self):
        """Initialize key loader."""
        if not HSM_AVAILABLE:
            raise RuntimeError(
                "HSM not available. Install python-pkcs11 and configure SoftHSM."
            )
        
        self.hsm = get_hsm_manager()
        self._cache = {}
        self._lock = Lock()
        
        logger.info("Initialized BFV key loader with SoftHSM")
    
    def load_public_key(self, use_cache: bool = True) -> bytes:
        """
        Load public key from HSM.
        
        Args:
            use_cache: Use cached key if available
            
        Returns:
            Serialized public key
            
        Security:
            Public keys are not sensitive and can be cached.
        """
        return self._load_key(self.PUBLIC_KEY_LABEL, use_cache)
    
    def load_secret_key(self, use_cache: bool = False) -> bytes:
        """
        Load secret key from HSM.
        
        Args:
            use_cache: Use cached key (NOT recommended for security)
            
        Returns:
            Serialized secret key
            
        Security WARNING:
            Secret keys should be loaded only when needed for decryption.
            Avoid caching in production environments.
        """
        logger.warning("Loading secret key from HSM (sensitive operation)")
        return self._load_key(self.SECRET_KEY_LABEL, use_cache)
    
    def load_relin_key(self, use_cache: bool = True) -> bytes:
        """
        Load relinearization key from HSM.
        
        Args:
            use_cache: Use cached key
            
        Returns:
            Serialized relinearization key
            
        Purpose:
            Relinearization keys are required for ciphertext multiplication.
            They enable reduction of ciphertext size after multiplication.
        """
        return self._load_key(self.RELIN_KEY_LABEL, use_cache)
    
    def load_galois_keys(self, use_cache: bool = True) -> bytes:
        """
        Load Galois rotation keys from HSM.
        
        Args:
            use_cache: Use cached keys
            
        Returns:
            Serialized Galois keys
            
        Purpose:
            Galois keys enable rotation operations on ciphertext slots.
            Required for computing encrypted Hamming distance via
            binary-tree reduction.
        """
        return self._load_key(self.GALOIS_KEY_LABEL, use_cache)
    
    def _load_key(self, label: str, use_cache: bool) -> bytes:
        """
        Internal method to load key with caching.
        
        Args:
            label: HSM key label
            use_cache: Whether to use cache
            
        Returns:
            Key bytes
        """
        with self._lock:
            # Check cache first
            if use_cache and label in self._cache:
                logger.debug(f"Using cached key: {label}")
                return self._cache[label]
            
            # Load from HSM
            try:
                key_bytes = self.hsm.retrieve_secret(label)
                logger.info(f"Loaded key from HSM: {label} ({len(key_bytes)} bytes)")
                
                # Cache it
                if use_cache:
                    self._cache[label] = key_bytes
                
                return key_bytes
                
            except ValueError as e:
                logger.error(f"Key not found in HSM: {label}")
                raise ValueError(f"BFV key '{label}' not found in HSM") from e
            except Exception as e:
                logger.error(f"Failed to load key: {e}")
                raise
    
    def load_all_keys(
        self,
        include_secret: bool = False
    ) -> Tuple[bytes, Optional[bytes], bytes, bytes]:
        """
        Load all BFV keys.
        
        Args:
            include_secret: Whether to load secret key
            
        Returns:
            Tuple of (public_key, secret_key, relin_key, galois_keys)
            
        Usage:
            For server-side encryption: include_secret=False
            For decryption: include_secret=True
        """
        public_key = self.load_public_key()
        secret_key = self.load_secret_key() if include_secret else None
        relin_key = self.load_relin_key()
        galois_keys = self.load_galois_keys()
        
        logger.info(
            f"Loaded all keys (secret_key_included={include_secret})"
        )
        
        return public_key, secret_key, relin_key, galois_keys
    
    def clear_cache(self) -> None:
        """
        Clear key cache and zeroize memory.
        
        Security:
            Best-effort memory zeroization.
            Python's GC may leave copies in memory.
        """
        with self._lock:
            from ..utils.secure_zero import secure_zero_bytes
            
            for label, key_bytes in self._cache.items():
                secure_zero_bytes(bytearray(key_bytes))
                logger.debug(f"Zeroized cached key: {label}")
            
            self._cache.clear()
            logger.info("Key cache cleared")
    
    def store_key(self, label: str, key_bytes: bytes) -> bool:
        """
        Store BFV key in HSM.
        
        Args:
            label: Key label
            key_bytes: Serialized key
            
        Returns:
            True if stored successfully
            
        Note:
            This should be called only during key generation phase.
        """
        try:
            self.hsm.store_secret_test(label, key_bytes)
            logger.info(f"Stored key in HSM: {label} ({len(key_bytes)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to store key: {e}")
            return False
    
    def key_exists(self, label: str) -> bool:
        """
        Check if key exists in HSM.
        
        Args:
            label: Key label
            
        Returns:
            True if key exists
        """
        try:
            self.hsm.retrieve_secret(label)
            return True
        except ValueError:
            return False
