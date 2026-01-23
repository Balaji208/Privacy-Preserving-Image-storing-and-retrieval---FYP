"""
Image Processor for Query Pipeline
===================================
Handles feature extraction + hash generation for query images (v4.0)
"""

import logging
import numpy as np
from pathlib import Path
from typing import Tuple

# Import from same modules as storage_pipeline
from feature_extractor import ConvNeXtFeatureExtractor
from deephashing import DeepHashGenerator, DeepHashingConfig

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Processes query images: Feature extraction + DeepHash v4.0 (direct mode, no PCA)."""
    
    def __init__(
        self,
        convnext_model_path: str = './models/convnextv2_best_phase1.pt',
        deephash_model_path: str = './models/deephash_v4_state_dict.pt',
        device: str = 'cuda'
    ):
        """
        Initialize feature extractor and hash generator (v4.0).
        
        Args:
            convnext_model_path: Path to ConvNeXt-V2 model
            deephash_model_path: Path to DeepHash v4.0 weights
            device: Device to run on ('cuda' or 'cpu')
        
        Note:
            v4.0 uses direct mode (512D → 256-bit) without PCA preprocessing.
        """
        logger.info("[ImageProcessor] Initializing v4.0 (direct mode, no PCA)...")
        
        # Feature extraction (512D)
        logger.info(f"[ImageProcessor] Loading ConvNeXt-V2 from {convnext_model_path}")
        self.feature_extractor = ConvNeXtFeatureExtractor(
            model_path=convnext_model_path,
            device=device
        )
        logger.info("[ImageProcessor] ✓ ConvNeXt-V2 loaded (512D features)")
        
        # Hash generation v4.0 (direct: 512D → 256-bit, no PCA)
        logger.info(f"[ImageProcessor] Loading DeepHash v4.0 from {deephash_model_path}")
        config = DeepHashingConfig(
            hash_model_path=deephash_model_path,
            pca_transform_path=None,  # No PCA for v4.0!
            feature_dim=512,
            hash_bits=256,
            hidden_dims=[1024, 512],  # v4.0 architecture
            similarity_threshold=66,
            device=device
        )
        
        self.hash_generator = DeepHashGenerator(config=config)
        logger.info("[ImageProcessor] ✓ DeepHash v4.0 loaded (direct mode, no PCA)")
        logger.info("[ImageProcessor] ✓ Architecture: 512D → [1024, 512] → 256-bit")
        logger.info("[ImageProcessor] ✓ Ready")
    
    def process(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process image to extract features and generate hash.
        
        Args:
            image_path: Path to query image
        
        Returns:
            Tuple of (features, binary_hash)
            - features: (512,) float32 array
            - binary_hash: (256,) uint8 array of {0, 1}
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        logger.debug(f"[ImageProcessor] Processing: {image_path.name}")
        
        # Extract features (512D from ConvNeXt-V2)
        logger.debug("[ImageProcessor] Extracting CNN features...")
        features = self.feature_extractor.extract(str(image_path))
        logger.debug(f"[ImageProcessor] ✓ Features: shape={features.shape}")
        
        # Validate feature dimensions
        if features.shape[-1] != 512:
            raise ValueError(
                f"Expected 512D features, got {features.shape[-1]}D. "
                "Ensure you're using the correct ConvNeXt-V2 model."
            )
        
        # Generate hash (v4.0 direct: 512D → 256-bit, no PCA)
        logger.debug("[ImageProcessor] Generating deep hash (v4.0 direct mode)...")
        binary_hash, continuous_hash = self.hash_generator.generate_hash(features)
        
        # Ensure correct format
        if binary_hash.ndim > 1:
            binary_hash = binary_hash.squeeze()
        
        if binary_hash.shape != (256,):
            raise ValueError(
                f"Expected 256-bit hash, got {binary_hash.shape}. "
                "Check deep hash model configuration."
            )
        
        if binary_hash.dtype != np.uint8:
            binary_hash = binary_hash.astype(np.uint8)
        
        ones_count = int(np.sum(binary_hash))
        logger.debug(
            f"[ImageProcessor] ✓ Hash: {binary_hash.shape}, "
            f"ones={ones_count}/256 ({ones_count/256*100:.1f}%)"
        )
        
        return features, binary_hash
    
    def compute_similarity(
        self,
        hash1: np.ndarray,
        hash2: np.ndarray
    ) -> dict:
        """
        Compute similarity between two hash codes.
        
        Args:
            hash1: Binary hash [256]
            hash2: Binary hash [256]
        
        Returns:
            {
                'hamming_distance': int,
                'similarity_score': float,
                'is_similar': bool,
                'confidence': str
            }
        """
        return self.hash_generator.compute_similarity(hash1, hash2)
    
    def get_info(self) -> dict:
        """Get processor information."""
        return {
            'feature_extractor': self.feature_extractor.get_info(),
            'hash_generator': self.hash_generator.get_info(),
            'pipeline': {
                'version': '4.0',
                'mode': 'Direct (no PCA)',
                'input': 'RGB image',
                'feature_extraction': 'ConvNeXt-V2 → 512D',
                'hashing': 'DeepHash v4.0 → 512D → [1024, 512] → 256 bits',
                'expected_similar_distance': '40-66 bits (high confidence)',
                'expected_dissimilar_distance': '120+ bits (very low confidence)',
                'similarity_threshold': '66 bits'
            }
        }
