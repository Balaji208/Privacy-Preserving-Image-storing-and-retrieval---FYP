"""
Binary Hash Encoder
===================
Encodes binary hashes into BFV plaintext slots for encryption.

Design:
    Binary vectors {0,1}^n are encoded into polynomial slots.
    Each bit occupies one slot, enabling slot-wise operations.
    
    For 256-bit hash with n=8192 slots:
        [b0, b1, ..., b255, 0, 0, ..., 0]
         ^-- hash bits --^   ^-- padding --^

Batching Benefits:
    - Parallel operations on all bits
    - Efficient XOR via addition mod 2
    - SIMD-style evaluation
"""

import numpy as np
from typing import Union, List
import logging

logger = logging.getLogger(__name__)


class BinaryEncoder:
    """
    Encodes binary hashes for BFV encryption.
    
    Handles:
        - Binary vector → plaintext slots
        - Padding to slot capacity
        - Modulo reduction
        - Decoding with validation
    
    Attributes:
        num_slots: Number of polynomial slots
        plain_modulus: Plaintext modulus (for mod reduction)
    """
    
    def __init__(self, num_slots: int, plain_modulus: int):
        """
        Initialize binary encoder.
        
        Args:
            num_slots: Number of available slots (typically n/2)
            plain_modulus: Plaintext modulus
        """
        self.num_slots = num_slots
        self.plain_modulus = plain_modulus
        
        logger.info(
            f"Initialized binary encoder: slots={num_slots}, "
            f"plain_mod={plain_modulus}"
        )
    
    def encode(
        self,
        binary_hash: Union[np.ndarray, List[int]],
        validate: bool = True
    ) -> np.ndarray:
        """
        Encode binary hash into plaintext slots.
        
        Args:
            binary_hash: Binary vector {0,1}^k where k ≤ num_slots
            validate: Validate input format
            
        Returns:
            Padded integer array of length num_slots
            
        Process:
            1. Validate binary format
            2. Pad to num_slots
            3. Apply modulo reduction
            
        Example:
            >>> encoder = BinaryEncoder(num_slots=8192, plain_modulus=1024)
            >>> hash_256 = np.random.randint(0, 2, 256)
            >>> encoded = encoder.encode(hash_256)
            >>> encoded.shape
            (8192,)
            >>> encoded[:256]  # Original bits
            >>> encoded[256:]  # Zeros (padding)
        """
        # Convert to numpy
        if isinstance(binary_hash, list):
            binary_hash = np.array(binary_hash, dtype=np.int64)
        
        # Validate
        if validate:
            self._validate_binary(binary_hash)
        
        hash_length = len(binary_hash)
        
        if hash_length > self.num_slots:
            raise ValueError(
                f"Binary hash length ({hash_length}) exceeds "
                f"available slots ({self.num_slots})"
            )
        
        # Pad to num_slots
        padded = np.zeros(self.num_slots, dtype=np.int64)
        padded[:hash_length] = binary_hash
        
        # Apply modulo (for safety)
        padded = padded % self.plain_modulus
        
        logger.debug(
            f"Encoded binary hash: length={hash_length}, "
            f"padded_to={self.num_slots}"
        )
        
        return padded
    
    def decode(
        self,
        plaintext_slots: np.ndarray,
        hash_length: int
    ) -> np.ndarray:
        """
        Decode plaintext slots back to binary hash.
        
        Args:
            plaintext_slots: Decoded slots from plaintext
            hash_length: Original hash length (to remove padding)
            
        Returns:
            Binary hash of length hash_length
            
        Note:
            After homomorphic operations, values may not be exactly {0,1}.
            We apply modulo 2 to recover binary form.
        """
        if len(plaintext_slots) < hash_length:
            raise ValueError(
                f"Plaintext has {len(plaintext_slots)} slots but "
                f"expected at least {hash_length}"
            )
        
        # Extract first hash_length values
        decoded = plaintext_slots[:hash_length]
        
        # Reduce modulo 2 for binary recovery
        binary = decoded % 2
        
        logger.debug(f"Decoded to binary hash of length {hash_length}")
        
        return binary.astype(np.int64)
    
    def encode_batch(
        self,
        binary_hashes: List[np.ndarray]
    ) -> List[np.ndarray]:
        """
        Encode multiple binary hashes.
        
        Args:
            binary_hashes: List of binary vectors
            
        Returns:
            List of encoded slot arrays
        """
        return [self.encode(h) for h in binary_hashes]
    
    def _validate_binary(self, binary_hash: np.ndarray) -> None:
        """
        Validate binary hash format.
        
        Args:
            binary_hash: Array to validate
            
        Raises:
            ValueError: If format is invalid
        """
        if not isinstance(binary_hash, np.ndarray):
            raise ValueError(
                f"Binary hash must be numpy array, got {type(binary_hash)}"
            )
        
        if binary_hash.ndim != 1:
            raise ValueError(
                f"Binary hash must be 1D array, got shape {binary_hash.shape}"
            )
        
        # Check values are in {0, 1}
        unique_vals = np.unique(binary_hash)
        if not np.all(np.isin(unique_vals, [0, 1])):
            raise ValueError(
                f"Binary hash must contain only 0 and 1, got {unique_vals}"
            )
    
    def compute_hamming_slots(
        self,
        hash1_slots: np.ndarray,
        hash2_slots: np.ndarray
    ) -> np.ndarray:
        """
        Compute XOR slots for Hamming distance (plaintext).
        
        Args:
            hash1_slots: First hash (encoded slots)
            hash2_slots: Second hash (encoded slots)
            
        Returns:
            XOR result in slots
            
        Theory:
            Hamming distance = sum of XOR bits
            XOR(a, b) = (a + b) mod 2
        """
        xor_result = (hash1_slots + hash2_slots) % 2
        return xor_result
    
    def get_info(self) -> dict:
        """Get encoder information."""
        return {
            'num_slots': self.num_slots,
            'plain_modulus': self.plain_modulus,
            'max_hash_length': self.num_slots
        }
