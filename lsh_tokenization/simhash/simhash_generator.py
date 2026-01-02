"""
SimHash LSH Generator
=====================
Generates LSH bucket IDs from binary hashes.
"""

import numpy as np
from typing import List, Tuple
import logging

from ..config.lsh_config import LSHConfig
from ..utils.bit_utils import BitUtils
from .projections import RandomProjections

logger = logging.getLogger(__name__)


class SimHashGenerator:
    """
    SimHash-based LSH bucket ID generator.
    
    Generates L bucket IDs from a binary hash using random projections.
    Each bucket ID is an integer in range [0, 2^K - 1].
    
    Attributes:
        config: LSH configuration
        projections: Random projection manager
    """
    
    def __init__(self, config: LSHConfig):
        """
        Initialize SimHash generator.
        
        Args:
            config: LSH configuration
        """
        self.config = config
        self.projections = RandomProjections(
            hash_length=config.hash_length,
            num_tables=config.num_tables,
            bits_per_table=config.bits_per_table,
            seed=config.random_seed
        )
        
        logger.info(
            f"Initialized SimHash generator: L={config.num_tables}, "
            f"K={config.bits_per_table}"
        )
    
    def generate_bucket_ids(self, binary_hash: np.ndarray) -> List[int]:
        """
        Generate LSH bucket IDs for binary hash.
        
        Args:
            binary_hash: Binary hash (length: hash_length)
            
        Returns:
            List of L bucket IDs, each in range [0, 2^K - 1]
            
        Raises:
            ValueError: If binary_hash format is invalid
            
        Example:
            >>> generator = SimHashGenerator(config)
            >>> binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
            >>> bucket_ids = generator.generate_bucket_ids(binary_hash)
            >>> len(bucket_ids)
            6
            >>> all(0 <= bid < 4096 for bid in bucket_ids)
            True
        """
        # Validate input
        BitUtils.validate_binary_hash(binary_hash, self.config.hash_length)
        
        # Project to all tables
        projected_hashes = self.projections.project_all(binary_hash)
        
        # Convert each projected hash to integer bucket ID
        bucket_ids = [
            BitUtils.binary_to_int(projected)
            for projected in projected_hashes
        ]
        
        logger.debug(
            f"Generated {len(bucket_ids)} bucket IDs: "
            f"{bucket_ids[:3]}... (showing first 3)"
        )
        
        return bucket_ids
    
    def generate_with_metadata(
        self,
        binary_hash: np.ndarray
    ) -> List[Tuple[int, int, np.ndarray]]:
        """
        Generate bucket IDs with metadata for debugging.
        
        Args:
            binary_hash: Binary hash
            
        Returns:
            List of tuples: (table_idx, bucket_id, projected_bits)
        """
        BitUtils.validate_binary_hash(binary_hash, self.config.hash_length)
        
        results = []
        for table_idx in range(self.config.num_tables):
            projected = self.projections.project(binary_hash, table_idx)
            bucket_id = BitUtils.binary_to_int(projected)
            results.append((table_idx, bucket_id, projected))
        
        return results
    
    def estimate_collision_probability(
        self,
        hamming_distance: int
    ) -> float:
        """
        Estimate collision probability for given Hamming distance.
        
        Args:
            hamming_distance: Hamming distance between two hashes
            
        Returns:
            Estimated probability of collision in at least one table
            
        Theory:
            For K bits, collision probability ≈ (1 - d/n)^K
            where d is Hamming distance and n is hash length.
            Probability of collision in at least one of L tables:
            P = 1 - (1 - p_single)^L
        """
        if hamming_distance >= self.config.hash_length:
            return 0.0
        
        # Probability for single table
        p_single = (1.0 - hamming_distance / self.config.hash_length) ** self.config.bits_per_table
        
        # Probability for at least one table
        p_any = 1.0 - (1.0 - p_single) ** self.config.num_tables
        
        return p_any
