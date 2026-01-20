"""
Bit Manipulation Utilities
===========================
Low-level bit operations for binary hash processing.
"""

import numpy as np
from typing import Union, List
import logging

logger = logging.getLogger(__name__)


class BitUtils:
    """Utility functions for binary hash manipulation."""
    
    @staticmethod
    def binary_to_int(binary_array: np.ndarray) -> int:
        """
        Convert binary array to integer.
        
        Args:
            binary_array: Binary array (values in {0, 1})
            
        Returns:
            Integer representation
            
        Example:
            >>> binary_to_int(np.array([1, 0, 1, 1]))
            11  # (1*8 + 0*4 + 1*2 + 1*1)
        """
        if not isinstance(binary_array, np.ndarray):
            binary_array = np.array(binary_array)
        
        if binary_array.dtype != np.uint8 and binary_array.dtype != np.int64:
            binary_array = binary_array.astype(np.uint8)
        
        # Convert using powers of 2
        powers = 2 ** np.arange(len(binary_array) - 1, -1, -1)
        return int(np.dot(binary_array, powers))
    
    @staticmethod
    def int_to_binary(value: int, length: int) -> np.ndarray:
        """
        Convert integer to binary array of fixed length.
        
        Args:
            value: Integer to convert
            length: Length of output binary array
            
        Returns:
            Binary array of specified length
            
        Raises:
            ValueError: If value requires more bits than length
        """
        if value >= 2 ** length:
            raise ValueError(
                f"Value {value} requires more than {length} bits"
            )
        
        # Convert to binary string and pad
        binary_str = format(value, f'0{length}b')
        return np.array([int(b) for b in binary_str], dtype=np.uint8)
    
    @staticmethod
    def extract_bits(
        binary_hash: np.ndarray,
        start_idx: int,
        num_bits: int
    ) -> np.ndarray:
        """
        Extract contiguous bits from binary hash.
        
        Args:
            binary_hash: Full binary hash
            start_idx: Starting bit index
            num_bits: Number of bits to extract
            
        Returns:
            Extracted bits as binary array
            
        Raises:
            ValueError: If indices are out of bounds
        """
        if start_idx < 0 or start_idx >= len(binary_hash):
            raise ValueError(
                f"start_idx {start_idx} out of bounds for hash length {len(binary_hash)}"
            )
        
        end_idx = start_idx + num_bits
        if end_idx > len(binary_hash):
            raise ValueError(
                f"Cannot extract {num_bits} bits starting at {start_idx} "
                f"from hash of length {len(binary_hash)}"
            )
        
        return binary_hash[start_idx:end_idx]
    
    @staticmethod
    def hamming_distance(hash1: np.ndarray, hash2: np.ndarray) -> int:
        """
        Compute Hamming distance between two binary hashes.
        
        Args:
            hash1: First binary hash
            hash2: Second binary hash
            
        Returns:
            Hamming distance (number of differing bits)
            
        Raises:
            ValueError: If hashes have different lengths
        """
        if len(hash1) != len(hash2):
            raise ValueError(
                f"Hash lengths must match: {len(hash1)} vs {len(hash2)}"
            )
        
        return int(np.sum(hash1 != hash2))
    
    @staticmethod
    def validate_binary_hash(binary_hash: np.ndarray, expected_length: int) -> None:
        """
        Validate binary hash format.
        
        Args:
            binary_hash: Binary hash to validate
            expected_length: Expected length in bits
            
        Raises:
            ValueError: If hash is invalid
        """
        if not isinstance(binary_hash, np.ndarray):
            raise ValueError(
                f"binary_hash must be numpy array, got {type(binary_hash)}"
            )
        
        if len(binary_hash) != expected_length:
            raise ValueError(
                f"Expected hash length {expected_length}, got {len(binary_hash)}"
            )
        
        if not np.all(np.isin(binary_hash, [0, 1])):
            raise ValueError(
                "binary_hash must contain only 0 and 1 values"
            )
    
    @staticmethod
    def normalize_binary_hash(binary_hash: Union[np.ndarray, List[int]]) -> np.ndarray:
        """
        Normalize input to standard binary hash format.
        
        Args:
            binary_hash: Binary hash in various formats
            
        Returns:
            Normalized numpy array of uint8
        """
        if isinstance(binary_hash, list):
            binary_hash = np.array(binary_hash)
        
        if not isinstance(binary_hash, np.ndarray):
            raise ValueError(
                f"Cannot normalize type {type(binary_hash)} to binary hash"
            )
        
        # Convert to uint8 if needed
        if binary_hash.dtype != np.uint8:
            binary_hash = binary_hash.astype(np.uint8)
        
        return binary_hash
