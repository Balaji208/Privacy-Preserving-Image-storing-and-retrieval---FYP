"""
Feature Extraction Processor
=============================
Extracts 512D features using ConvNeXt-V2 (Updated for correct config API)
"""

import logging
import numpy as np
from pathlib import Path
from feature_extractor import ConvNeXtFeatureExtractor

logger = logging.getLogger(__name__)


class FeatureProcessor:
    """Handles feature extraction using ConvNeXt-V2."""
    
    def __init__(
        self,
        model_path: str = './models/convnext_v2_best_phase1.pt',
        device: str = 'cuda'
    ):
        """
        Initialize feature extractor.
        
        Args:
            model_path: Path to ConvNeXt model weights
            device: Device to run on ('cuda' or 'cpu')
        """
        model_path = Path(model_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"ConvNeXt model not found: {model_path}")
        
        # Initialize extractor with direct path (uses your existing API)
        self.extractor = ConvNeXtFeatureExtractor(
            model_path=str(model_path),
            device=device
        )
        
        logger.info("✓ Feature processor initialized")
        logger.info(f"  Model: {model_path.name}")
        logger.info(f"  Features: 512D")
        logger.info(f"  Device: {device}")
    
    def extract(self, image_path: str) -> np.ndarray:
        """
        Extract 512D features from image.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Feature vector [512] (numpy array, float32)
        """
        features = self.extractor.extract(image_path)
        
        # Ensure correct shape and type
        if features.ndim > 1:
            features = features.squeeze()
        
        if features.dtype != np.float32:
            features = features.astype(np.float32)
        
        logger.debug(f"✓ Features extracted: {features.shape}")
        
        return features
    
    def extract_batch(self, image_paths: list) -> np.ndarray:
        """
        Extract features from multiple images.
        
        Args:
            image_paths: List of image paths
        
        Returns:
            Feature batch [N, 512]
        """
        features = self.extractor.extract_batch(image_paths)
        
        logger.debug(f"✓ Batch features extracted: {features.shape}")
        
        return features
