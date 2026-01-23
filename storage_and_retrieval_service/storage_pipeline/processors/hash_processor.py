"""
DeepHash Processor
==================
Generates 256-bit binary hash from 512D features using DeepHash v4.0 (direct mode)
"""

import logging
import numpy as np
from pathlib import Path
from deephashing import DeepHashGenerator, DeepHashingConfig

logger = logging.getLogger(__name__)


class HashProcessor:
    """Handles DeepHash v4.0 generation (direct mode, no PCA)."""
    
    def __init__(
        self,
        model_path: str = './models/deephash_v4_statedict.pt',
        device: str = 'cuda'
    ):
        """
        Initialize DeepHash v4.0 generator (direct mode).
        
        Args:
            model_path: Path to DeepHash v4.0 model weights
            device: Device to run on ('cuda' or 'cpu')
        
        Note:
            v4.0 uses direct hashing (512D → 256-bit) without PCA preprocessing.
        """
        model_path = Path(model_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"DeepHash model not found: {model_path}")
        
        # Create config for v4.0 (direct mode - no PCA)
        config = DeepHashingConfig(
            hash_model_path=str(model_path),
            pca_transform_path=None,  # No PCA for v4.0
            feature_dim=512,
            hash_bits=256,
            hidden_dims=[1024, 512],  # v4.0 architecture
            dropout=0.2,
            similarity_threshold=66,  # Based on v4.0 validation
            device=device
        )
        
        # Initialize generator
        self.generator = DeepHashGenerator(config=config)
        
        logger.info("✓ Hash processor initialized (DeepHash v4.0)")
        logger.info(f"  Model: {model_path.name}")
        logger.info(f"  Mode: Direct (512D → 256-bit, no PCA)")
        logger.info(f"  Architecture: 512D → [1024, 512] → 256-bit")
        logger.info(f"  Similarity threshold: 66 bits")
        logger.info(f"  Device: {device}")
    
    def generate(self, features: np.ndarray) -> np.ndarray:
        """
        Generate 256-bit binary hash from 512D features.
        
        Args:
            features: Feature vector [512] or batch [N, 512]
        
        Returns:
            Binary hash [256] in {0, 1} (uint8)
        """
        # Validate input
        if features.ndim == 1:
            expected_dim = 512
        else:
            expected_dim = features.shape[-1]
        
        if expected_dim != 512:
            raise ValueError(
                f"Expected 512D features, got {expected_dim}D. "
                "v4.0 model uses direct 512D input (no PCA)."
            )
        
        # Generate hash (returns binary and continuous)
        binary_hash, continuous_hash = self.generator.generate_hash(features)
        
        # Ensure correct format
        if binary_hash.ndim > 1:
            binary_hash = binary_hash.squeeze()
        
        # Convert to uint8 if needed
        if binary_hash.dtype != np.uint8:
            binary_hash = binary_hash.astype(np.uint8)
        
        # Log statistics
        hash_sum = int(np.sum(binary_hash))
        logger.debug(f"✓ Hash generated: {binary_hash.shape}, ones={hash_sum}/256")
        
        return binary_hash
    
    def generate_batch(self, features_batch: np.ndarray) -> np.ndarray:
        """
        Generate hashes for batch of features.
        
        Args:
            features_batch: Feature batch [N, 512]
        
        Returns:
            Binary hashes [N, 256]
        """
        if features_batch.shape[-1] != 512:
            raise ValueError(f"Expected 512D features, got {features_batch.shape[-1]}D")
        
        binary_hashes, _ = self.generator.generate_hash(features_batch)
        
        if binary_hashes.dtype != np.uint8:
            binary_hashes = binary_hashes.astype(np.uint8)
        
        logger.debug(f"✓ Batch hashes generated: {binary_hashes.shape}")
        
        return binary_hashes
    
    def compute_similarity(self, hash1: np.ndarray, hash2: np.ndarray) -> dict:
        """
        Compute similarity between two hashes.
        
        Args:
            hash1: Binary hash [256]
            hash2: Binary hash [256]
        
        Returns:
            {
                'hamming_distance': int (0-256),
                'similarity_score': float (0-1),
                'is_similar': bool,
                'confidence': str ('very_high', 'high', 'medium', 'low', 'very_low')
            }
        """
        return self.generator.compute_similarity(hash1, hash2)
    
    def get_info(self) -> dict:
        """Get hash processor information."""
        return self.generator.get_info()
