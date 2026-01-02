"""
DeepHashing Package
===================
Binary hash code generation for medical image retrieval.

Usage:
    from deephashing import DeepHashGenerator
    
    generator = DeepHashGenerator('models/deephash.pt')
    hash_code = generator.generate(features)
"""

from .generator import DeepHashGenerator
from .core.model import DeepHashingHead
from .exceptions import (
    DeepHashError,
    ModelLoadError,
    ValidationError
)

__version__ = "1.0.0"
__all__ = [
    "DeepHashGenerator",
    "DeepHashingHead",
    "DeepHashError",
    "ModelLoadError",
    "ValidationError"
]
