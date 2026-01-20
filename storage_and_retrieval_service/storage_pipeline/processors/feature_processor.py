"""
Feature Extraction Processor
=============================
Extracts features using ConvNeXt-V2
"""

import logging
import numpy as np
from feature_extractor import ConvNeXtFeatureExtractor

logger = logging.getLogger(__name__)

class FeatureProcessor:
    """Handles feature extraction."""
    
    def __init__(self, model_path: str = './models/convnext_state_dict_only.pt'):
        """Initialize feature extractor."""
        self.extractor = ConvNeXtFeatureExtractor(model_path=model_path)
        logger.info("✓ Feature processor initialized")
    
    def extract(self, image_path: str) -> np.ndarray:
        """
        Extract features from image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Feature vector (512-dim)
        """
        features = self.extractor.extract(image_path)
        logger.debug(f"✓ Features extracted: {features.shape}")
        return features
