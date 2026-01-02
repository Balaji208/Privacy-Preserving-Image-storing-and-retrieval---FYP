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
