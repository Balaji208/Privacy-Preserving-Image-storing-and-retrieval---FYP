"""Custom exceptions for feature extraction"""


class FeatureExtractionError(Exception):
    """Base exception for feature extraction errors"""
    pass


class ModelLoadError(FeatureExtractionError):
    """Raised when model loading fails"""
    pass


class ImageLoadError(FeatureExtractionError):
    """Raised when image loading fails"""
    pass


class ConfigurationError(FeatureExtractionError):
    """Raised when configuration is invalid"""
    pass
