"""
Feature Extraction Package
===========================
ConvNeXt-V2 based feature extraction for medical images.

Usage:
    from feature_extractor import ConvNeXtFeatureExtractor
    
    extractor = ConvNeXtFeatureExtractor('models/convnext.pt')
    features = extractor.extract('image.jpg')
"""

from .extractor import ConvNeXtFeatureExtractor
from .core.model import ConvNeXtV2FeatureExtractor
from .exceptions import (
    FeatureExtractionError,
    ModelLoadError,
    ImageLoadError
)

__version__ = "1.0.0"
__all__ = [
    "ConvNeXtFeatureExtractor",
    "ConvNeXtV2FeatureExtractor",
    "FeatureExtractionError",
    "ModelLoadError",
    "ImageLoadError"
]
