"""
FHE Encryption Processor
=========================

Encrypts hashes using TenSEAL BFV with HSM integration
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

class FHEProcessor:
    """Handles FHE encryption of hashes using production HSM backend."""
    
    def __init__(self):
        """Initialize FHE context from HSM."""
        try:
            from fhe_encryption import BFVPipeline
            
            # Use production FHE pipeline (TenSEAL + SoftHSM)
            self.fhe_pipeline = BFVPipeline(load_secret_key=False)
            logger.info("✓ FHE processor initialized (TenSEAL + SoftHSM)")
        except Exception as e:
            logger.error(f"Failed to initialize FHE: {e}")
            raise
    
    def encrypt(self, binary_hash: np.ndarray) -> bytes:
        """
        Encrypt binary hash using FHE.
        
        Args:
            binary_hash: Binary hash array (256-bit, uint8/int32)
        
        Returns:
            Serialized FHE ciphertext (~432KB)
        """
        # Ensure correct input format
        if binary_hash.shape != (256,):
            raise ValueError(f"Expected 256-bit hash, got {binary_hash.shape}")
        
        # Encrypt using production pipeline
        ciphertext = self.fhe_pipeline.encrypt(binary_hash)
        fhe_bytes = self.fhe_pipeline.serialize(ciphertext)
        
        logger.debug(f"✓ FHE encrypted: {len(fhe_bytes):,} bytes")
        return fhe_bytes
    
    def decrypt(self, fhe_bytes: bytes) -> np.ndarray:
        """
        Decrypt FHE ciphertext back to binary hash.
        
        Args:
            fhe_bytes: Serialized FHE ciphertext
        
        Returns:
            Decrypted 256-bit hash array
        
        Note:
            Requires secret key access (server-side only)
        """
        try:
            ciphertext = self.fhe_pipeline.deserialize(fhe_bytes)
            decrypted = self.fhe_pipeline.decrypt(ciphertext)
            
            # Ensure correct shape
            if decrypted.shape != (256,):
                logger.warning(f"FHE decrypt shape: {decrypted.shape}")
            
            return decrypted
        except Exception as e:
            logger.error(f"FHE decryption failed: {e}")
            raise
    
    def get_context_info(self) -> dict:
        """Get FHE context information."""
        return {
            'backend': 'TenSEAL + SoftHSM',
            'scheme': 'BFV',
            'security': '128-bit'
        }
