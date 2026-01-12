"""
Secure Image Storage Pipeline
==============================
Main module exports
"""

from .pipeline import SecureImagePipeline
from .models.metadata import ImageMetadata, ProcessingResult
from .config.azure_config import AzureStorageConfig
from .storage.azure_table_store import AzureTableKVStore

__all__ = [
    'SecureImagePipeline',
    'ImageMetadata',
    'ProcessingResult',
    'AzureStorageConfig',
    'AzureTableKVStore'
]

__version__ = '2.0.0'
