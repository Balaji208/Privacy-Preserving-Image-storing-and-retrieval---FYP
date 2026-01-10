"""
Secure Image Storage Pipeline
==============================
Complete pipeline for encrypted medical image storage and retrieval.
"""

from .image_processor import (
    SecureImageProcessor,
    ImageMetadata,
    process_single_image,
    process_batch
)

__all__ = [
    'SecureImageProcessor',
    'ImageMetadata',
    'process_single_image',
    'process_batch'
]

__version__ = '1.0.0'
