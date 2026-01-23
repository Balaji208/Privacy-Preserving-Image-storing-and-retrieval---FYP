"""
Query Pipeline Module
=====================

Prepares image queries for similarity search service.

Flow:
1. Load query image
2. Extract features (CNN features)
3. Generate perceptual hash (DeepHashing)
4. Generate LSH tokens (HMAC-based)
5. Encrypt hash with FHE (BFV)
6. Build request body for similarity service

Components:
- ImageProcessor: Feature extraction + hashing
- TokenGenerator: LSH token generation
- FHEEncryptor: Query encryption
- QueryPipeline: Main orchestrator
"""
from .image_processor import ImageProcessor
from .token_generator import TokenGenerator
from .fhe_encryptor import FHEEncryptor
from .pipeline import QueryPipeline

__all__ = [
    'ImageProcessor',
    'TokenGenerator',
    'FHEEncryptor',
    'QueryPipeline'
]