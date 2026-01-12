"""
DeepHash Processor
==================
Generates binary hash from features
"""

import logging
import numpy as np
from deephashing import DeepHashGenerator

logger = logging.getLogger(__name__)

class HashProcessor:
    """Handles DeepHash generation."""
    
    def __init__(self, model_path: str = './models/deephash_state_dict_only.pt'):
        """Initialize hash generator."""
        self.generator = DeepHashGenerator(model_path=model_path)
        logger.info("✓ Hash processor initialized")
    
    def generate(self, features: np.ndarray) -> np.ndarray:
        """
        Generate binary hash from features.
        
        Args:
            features: Feature vector
            
        Returns:
            Binary hash (256-bit)
        """
        hash_array = self.generator.generate(features)
        
        # Ensure uint8 format
        if hash_array.dtype != np.uint8:
            hash_array = hash_array.astype(np.uint8)
        
        logger.debug(f"✓ Hash generated: {hash_array.shape}, sum={np.sum(hash_array)}")
        return hash_array
