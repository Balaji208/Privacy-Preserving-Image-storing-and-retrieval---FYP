"""
FHE Encryption Processor
=========================
Encrypts hashes using TenSEAL BFV (Keyswitching Fixed)
"""

import logging
import numpy as np
import tenseal as ts

logger = logging.getLogger(__name__)

class FHEProcessor:
    """Handles FHE encryption of hashes."""
    
    def __init__(self):
        """Initialize FHE context."""
        self.context = self._create_context()
        logger.info("✓ FHE processor initialized")
    
    def _create_context(self) -> ts.Context:
        """Create FHE context with production-ready parameters."""
        # Use test_fhe.py working parameters (128-bit security)
        context = ts.context(
            ts.SCHEME_TYPE.BFV,
            poly_modulus_degree=4096,      # Matches test_fhe.py
            plain_modulus=1032193          # Matches test_fhe.py ✓
        )
        
        # NO Galois keys - we only need basic encryption/decryption
        # context.generate_galois_keys()  # ← This causes the error!
        
        # Make public for encryption (secret key stays for decryption)
        context.make_context_public()
        return context
    
    def encrypt(self, binary_hash: np.ndarray) -> bytes:
        """
        Encrypt binary hash using FHE.
        
        Args:
            binary_hash: Binary hash array (256-bit, uint8/int64)
            
        Returns:
            Serialized FHE ciphertext (~88KB)
        """
        # Ensure correct input format
        if binary_hash.shape != (256,):
            raise ValueError(f"Expected 256-bit hash, got {binary_hash.shape}")
            
        # Convert to int64 list
        hash_int64 = binary_hash.astype(np.int64).tolist()
        
        # Encrypt using public context
        fhe_encrypted = ts.bfv_vector(self.context, hash_int64)
        fhe_bytes = fhe_encrypted.serialize()
        
        logger.debug(f"✓ FHE encrypted: {len(fhe_bytes):,} bytes")
        return fhe_bytes
    
    def decrypt(self, fhe_bytes: bytes) -> np.ndarray:
        """
        Decrypt FHE ciphertext back to binary hash.
        
        Args:
            fhe_bytes: Serialized FHE ciphertext
            
        Returns:
            Decrypted 256-bit hash array
        """
        # Deserialize using same context
        fhe_vector = ts.bfv_vector_from(self.context, fhe_bytes)
        decrypted = np.array(fhe_vector.decrypt(), dtype=np.int64)
        
        # Verify shape
        if decrypted.shape != (256,):
            logger.warning(f"FHE decrypt shape: {decrypted.shape}")
            
        return decrypted

    def get_context_info(self) -> dict:
        """Debug info for context."""
        return {
            'scheme': 'BFV',
            'poly_modulus_degree': 4096,
            'plain_modulus': 1032193,
            'is_public': self.context.is_public(),
            'security_bits': '~128'
        }
