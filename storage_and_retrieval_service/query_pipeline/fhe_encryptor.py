"""
FHE Encryptor for Query Pipeline
=================================
Encrypts query hash using BFV (public context only)
"""

import logging
import numpy as np
import base64

logger = logging.getLogger(__name__)

class FHEEncryptor:
    """Encrypts query hashes using FHE (public context only)."""
    
    def __init__(self, context_path: str = './bfv_keys/bfv_context_public.bin'):
        """Initialize FHE with public context only (no secret key)."""
        logger.info("[FHEEncryptor] Loading BFV public context...")
        
        from fhe_encryption import BFVPipeline
        
        # Load public context only (for client-side encryption)
        self.fhe_pipeline = BFVPipeline(load_secret_key=False)
        
        logger.info(f"[FHEEncryptor] ✓ Context loaded from {context_path}")
    
    def encrypt(self, binary_hash: np.ndarray) -> str:
        """
        Encrypt binary hash using FHE.
        
        Args:
            binary_hash: (256,) array of 0/1
            
        Returns:
            Base64-encoded FHE ciphertext string
        """
        if binary_hash.shape != (256,):
            raise ValueError(f"Expected 256-bit hash, got {binary_hash.shape}")
        
        logger.debug(f"[FHEEncryptor] Encrypting {binary_hash.shape[0]}-bit hash...")
        
        # Encrypt
        ciphertext = self.fhe_pipeline.encrypt(binary_hash)
        
        # Serialize
        fhe_bytes = self.fhe_pipeline.serialize(ciphertext)
        
        # Encode to base64 string
        fhe_str = base64.b64encode(fhe_bytes).decode('utf-8')
        
        logger.debug(f"[FHEEncryptor] ✓ Encrypted: {len(fhe_bytes):,} bytes")
        
        return fhe_str
