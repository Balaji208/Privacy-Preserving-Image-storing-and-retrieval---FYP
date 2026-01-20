"""Distance and similarity metrics"""

import numpy as np
from typing import Union


class HashMetrics:
    """Compute hash-based metrics"""
    
    def __init__(self, hash_bits: int):
        self.hash_bits = hash_bits
    
    def hamming_distance(
        self,
        codes1: np.ndarray,
        codes2: np.ndarray
    ) -> Union[int, np.ndarray]:
        """
        Compute Hamming distance.
        
        Args:
            codes1: Binary codes (N, K) or (K,)
            codes2: Binary codes (M, K) or (K,)
            
        Returns:
            Hamming distance(s)
        """
        # Ensure 2D
        codes1 = np.atleast_2d(codes1)
        codes2 = np.atleast_2d(codes2)
        
        # Compute XOR and count
        distances = (
            codes1[:, np.newaxis, :] != codes2[np.newaxis, :, :]
        ).sum(axis=2)
        
        # Return appropriate shape
        return self._reshape_output(distances)
    
    def similarity(
        self,
        codes1: np.ndarray,
        codes2: np.ndarray
    ) -> Union[float, np.ndarray]:
        """
        Compute similarity score (1 - normalized Hamming distance).
        
        Args:
            codes1: Binary codes
            codes2: Binary codes
            
        Returns:
            Similarity scores in [0, 1]
        """
        distances = self.hamming_distance(codes1, codes2)
        return 1.0 - (distances / self.hash_bits)
    
    @staticmethod
    def _reshape_output(distances: np.ndarray) -> Union[int, np.ndarray]:
        """Reshape distance output appropriately"""
        if distances.shape == (1, 1):
            return int(distances[0, 0])
        elif distances.shape[0] == 1:
            return distances[0]
        elif distances.shape[1] == 1:
            return distances[:, 0]
        else:
            return distances
