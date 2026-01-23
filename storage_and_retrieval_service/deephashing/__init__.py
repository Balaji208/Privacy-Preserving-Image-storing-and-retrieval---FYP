"""
DeepHashing Package
===================

Binary hash code generation for medical image retrieval.

Usage:
    from deephashing import DeepHashGenerator, DeepHashingConfig
    
    config = DeepHashingConfig(
        hash_model_path='models/deephash_v4_statedict.pt',
        pca_transform_path='models/pca_whitening.pkl'
    )
    generator = DeepHashGenerator(config=config)
    binary, continuous = generator.generate_hash(features)
"""

from .generator import DeepHashGenerator
from .core.model import DeepHashingHead, DeepHashingModel
from .core.config import DeepHashingConfig
from .exceptions import (
    DeepHashError,
    ModelLoadError,
    ValidationError,
    HashGenerationError,
    PCATransformError,
    ModelInferenceError
)

__version__ = "2.0.0"
__author__ = "FYP Team"

__all__ = [
    "DeepHashGenerator",
    "DeepHashingHead",
    "DeepHashingModel",
    "DeepHashingConfig",
    "DeepHashError",
    "ModelLoadError",
    "ValidationError",
    "HashGenerationError",
    "PCATransformError",
    "ModelInferenceError"
]
