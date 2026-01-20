"""
BFV Encryptor
=============
Encrypts plaintext data using BFV public key.

Security:
    - Uses probabilistic encryption (fresh randomness per encryption)
    - Provides IND-CPA security
    - Post-quantum safe (RLWE assumption)
"""

from Pyfhel import PyCtxt
import numpy as np
from typing import Union, List
import logging

from ..context.bfv_context import BFVContext
from ..encoding.binary_encoder import BinaryEncoder

logger = logging.getLogger(__name__)


class BFVEncryptor:
    """
    BFV encryption operations.
    
    Encrypts binary hashes into homomorphic ciphertexts.
    
    Attributes:
        context: BFV context with loaded public key
        encoder: Binary encoder for slot packing
    """
    
    def __init__(self, context: BFVContext, encoder: BinaryEncoder):
        """
        Initialize encryptor.
        
        Args:
            context: Initialized BFV context with public key
            encoder: Binary encoder
            
        Raises:
            RuntimeError: If context not initialized
        """
        if not context.is_initialized:
            raise RuntimeError("BFV context not initialized")
        
        self.context = context
        self.encoder = encoder
        
        logger.info("Initialized BFV encryptor")
    
    def encrypt(self, binary_hash: np.ndarray) -> PyCtxt:
        """
        Encrypt binary hash.
        
        Args:
            binary_hash: Binary vector {0,1}^k
            
        Returns:
            BFV ciphertext
            
        Process:
            1. Encode binary hash into slots
            2. Convert to plaintext polynomial
            3. Encrypt using public key
            
        Security:
            Each encryption uses fresh randomness, providing
            probabilistic encryption (same plaintext → different ciphertexts).
            
        Example:
            >>> hash_256 = np.random.randint(0, 2, 256)
            >>> ctxt = encryptor.encrypt(hash_256)
            >>> type(ctxt)
            <class 'Pyfhel.PyCtxt'>
        """
        # Encode to slots
        slots = self.encoder.encode(binary_hash)
        
        # Create plaintext
        ptxt = self.context.encode(slots)
        
        # Encrypt
        ctxt = self.context.pyfhel.encrypt(ptxt)
        
        logger.debug(
            f"Encrypted binary hash of length {len(binary_hash)}"
        )
        
        return ctxt
    
    def encrypt_batch(
        self,
        binary_hashes: List[np.ndarray]
    ) -> List[PyCtxt]:
        """
        Encrypt multiple binary hashes.
        
        Args:
            binary_hashes: List of binary vectors
            
        Returns:
            List of ciphertexts
            
        Performance:
            Batch encryption is parallelizable at application level.
        """
        ciphertexts = []
        
        for i, binary_hash in enumerate(binary_hashes):
            ctxt = self.encrypt(binary_hash)
            ciphertexts.append(ctxt)
        
        logger.info(f"Encrypted {len(ciphertexts)} binary hashes")
        
        return ciphertexts
    
    def get_noise_budget(self, ciphertext: PyCtxt) -> int:
        """
        Get remaining noise budget.
        
        Args:
            ciphertext: Ciphertext to inspect
            
        Returns:
            Noise budget in bits
            
        Interpretation:
            - Fresh ciphertext: ~150-200 bits
            - After addition: ~1 bit consumed
            - After multiplication: ~30-50 bits consumed
            - Below 10 bits: risky, may fail decryption
        """
        return self.context.get_noise_budget(ciphertext)
