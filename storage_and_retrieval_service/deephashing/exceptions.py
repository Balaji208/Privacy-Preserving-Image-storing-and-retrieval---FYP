"""Custom exceptions for DeepHashing module"""

class DeepHashError(Exception):
    """Base exception for DeepHashing errors"""
    pass

class ModelLoadError(DeepHashError):
    """Raised when model loading fails"""
    pass

class ValidationError(DeepHashError):
    """Raised when input validation fails"""
    pass

class ConfigurationError(DeepHashError):
    """Raised when configuration is invalid"""
    pass

class HashGenerationError(DeepHashError):
    """Raised when hash generation fails"""
    pass

class FeatureExtractionError(DeepHashError):
    """Raised when feature extraction fails"""
    pass

class PCATransformError(DeepHashError):
    """Raised when PCA transformation fails"""
    pass

class ModelInferenceError(DeepHashError):
    """Raised when model inference fails"""
    pass
