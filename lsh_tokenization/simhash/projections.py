"""
Random Projection Generation
=============================
Manages random projection matrices for LSH tables.
"""

import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


class RandomProjections:
    """
    Manages random projection matrices for SimHash LSH.
    
    Each LSH table uses independent random projections to hash
    the input binary hash into a bucket ID.
    
    Attributes:
        hash_length: Length of input binary hash
        num_tables: Number of LSH tables
        bits_per_table: Bits used per table
        seed: Random seed for reproducibility
        projections: List of projection matrices
    """
    
    def __init__(
        self,
        hash_length: int,
        num_tables: int,
        bits_per_table: int,
        seed: int = 42
    ):
        """
        Initialize random projections.
        
        Args:
            hash_length: Length of input binary hash
            num_tables: Number of LSH tables (L)
            bits_per_table: Number of bits per table (K)
            seed: Random seed for reproducibility
        """
        self.hash_length = hash_length
        self.num_tables = num_tables
        self.bits_per_table = bits_per_table
        self.seed = seed
        
        # Generate projection matrices
        self.projections = self._generate_projections()
        
        logger.info(
            f"Initialized {self.num_tables} random projection matrices "
            f"({self.hash_length} → {self.bits_per_table} bits each)"
        )
    
    def _generate_projections(self) -> List[np.ndarray]:
        """
        Generate random projection matrices for all tables.
        
        Returns:
            List of L projection matrices, each of shape (K, hash_length)
            
        Design:
            Each table uses independent random projections sampled from
            {0, 1}. This is equivalent to randomly selecting K bits from
            the input hash for each table.
        """
        rng = np.random.RandomState(self.seed)
        projections = []
        
        for table_idx in range(self.num_tables):
            # For each table, randomly select bits_per_table indices
            # This is more efficient than full matrix multiplication
            indices = rng.choice(
                self.hash_length,
                size=self.bits_per_table,
                replace=False  # Sample without replacement
            )
            
            # Store as sorted indices for deterministic ordering
            indices = np.sort(indices)
            projections.append(indices)
        
        return projections
    
    def project(self, binary_hash: np.ndarray, table_idx: int) -> np.ndarray:
        """
        Project binary hash using specified table's projection.
        
        Args:
            binary_hash: Input binary hash (length: hash_length)
            table_idx: Index of LSH table to use
            
        Returns:
            Projected hash (length: bits_per_table)
            
        Raises:
            ValueError: If table_idx is out of range
        """
        if table_idx < 0 or table_idx >= self.num_tables:
            raise ValueError(
                f"table_idx {table_idx} out of range [0, {self.num_tables})"
            )
        
        # Extract bits at selected indices
        indices = self.projections[table_idx]
        projected = binary_hash[indices]
        
        return projected
    
    def project_all(self, binary_hash: np.ndarray) -> List[np.ndarray]:
        """
        Project binary hash using all tables.
        
        Args:
            binary_hash: Input binary hash
            
        Returns:
            List of L projected hashes
        """
        return [
            self.project(binary_hash, table_idx)
            for table_idx in range(self.num_tables)
        ]
    
    def get_projection_indices(self, table_idx: int) -> np.ndarray:
        """
        Get projection indices for a specific table.
        
        Args:
            table_idx: Index of LSH table
            
        Returns:
            Array of indices used by this table
        """
        if table_idx < 0 or table_idx >= self.num_tables:
            raise ValueError(
                f"table_idx {table_idx} out of range [0, {self.num_tables})"
            )
        
        return self.projections[table_idx].copy()
