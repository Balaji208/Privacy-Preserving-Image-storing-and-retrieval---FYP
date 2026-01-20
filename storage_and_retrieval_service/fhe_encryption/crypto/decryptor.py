"""
BFV Decryptor
=============
Decrypts BFV ciphertexts using secret key.

Security WARNING:
    Decryption should only be performed in trusted environments.
    Secret key must never leave secure boundaries.
"""

from Pyfhel import PyCtxt
import numpy as np
from typing import List
import logging

from ..context.bfv_context import BFVContext
from ..encoding.binary_encoder import BinaryEncoder

logger = logging.getLogger(__name__)


class BFVDecryptor:
    """
    BFV decryption operations.
    
    Decrypts ciphertexts back to plaintext using secret key.
    
    Attributes:
        context: BFV context with loaded secret key
        encoder: Binary encoder for slot decoding
    """
    
    def __init__(self, context: BFVContext, encoder: BinaryEncoder):
        """
        Initialize decryptor.
        
        Args:
            context: BFV context with secret key loaded
            encoder: Binary encoder
            
        Raises:
            RuntimeError: If secret key not loaded
        """
        if not context.is_initialized:
            raise RuntimeError("BFV context not initialized")
        
        # Check if secret key is loaded
        try:
            # Try a dummy decryption to verify
            dummy_ptxt = context.pyfhel.decryptPtxt(
                context.pyfhel.encryptPtxt(context.encode(np.array([1])))
            )
        except Exception:
            raise RuntimeError(
                "Secret key not loaded in context. "
                "Call context.load_keys() with secret_key parameter."
            )
        
        self.context = context
        self.encoder = encoder
        
        logger.info("Initialized BFV decryptor")
    
    def decrypt(
        self,
        ciphertext: PyCtxt,
        hash_length: int
    ) -> np.ndarray:
        """
        Decrypt ciphertext to binary hash.
        
        Args:
            ciphertext: Encrypted ciphertext
            hash_length: Original hash length (for padding removal)
            
        Returns:
            Binary hash {0,1}^hash_length
            
        Process:
            1. Decrypt ciphertext to plaintext
            2. Decode plaintext slots
            3. Extract first hash_length values
            4. Apply mod 2 for binary recovery
            
        Noise Handling:
            If noise budget is too low, decryption may fail or
            return incorrect values. Always check noise budget
            before critical operations.
        """
        # Check noise budget
        noise = self.context.get_noise_budget(ciphertext)
        if noise < 10:
            logger.warning(
                f"Low noise budget ({noise} bits). "
                f"Decryption may be unreliable."
            )
        
        # Decrypt to plaintext
        ptxt = self.context.pyfhel.decrypt(ciphertext)
        
        # Decode slots
        slots = self.context.decode(ptxt)
        
        # Extract and convert to binary
        binary_hash = self.encoder.decode(slots, hash_length)
        
        logger.debug(
            f"Decrypted to binary hash of length {hash_length} "
            f"(noise_budget={noise} bits)"
        )
        
        return binary_hash
    
    def decrypt_to_int(self, ciphertext: PyCtxt) -> int:
        """
        Decrypt ciphertext to single integer.
        
        Args:
            ciphertext: Encrypted integer
            
        Returns:
            Decrypted integer value
            
        Use Case:
            For decrypting Hamming distance results.
        """
        # Decrypt
        ptxt = self.context.pyfhel.decrypt(ciphertext)
        
        # Decode slots
        slots = self.context.decode(ptxt)
        
        # Return first slot value
        result = int(slots[0])
        
        logger.debug(f"Decrypted to integer: {result}")
        
        return result
    
    def decrypt_batch(
        self,
        ciphertexts: List[PyCtxt],
        hash_length: int
    ) -> List[np.ndarray]:
        """
        Decrypt multiple ciphertexts.
        
        Args:
            ciphertexts: List of ciphertexts
            hash_length: Original hash length
            
        Returns:
            List of binary hashes
        """
        results = []
        
        for ctxt in ciphertexts:
            binary_hash = self.decrypt(ctxt, hash_length)
            results.append(binary_hash)
        
        logger.info(f"Decrypted {len(results)} binary hashes")
        
        return results
