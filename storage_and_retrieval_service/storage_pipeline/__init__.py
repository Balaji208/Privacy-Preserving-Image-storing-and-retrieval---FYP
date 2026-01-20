"""
Secure Image Storage Pipeline
==============================

Main module exports
"""

from .pipeline import SecureImagePipeline
from .models.metadata import ImageMetadata, ProcessingResult
from .config.azure_config import AzureStorageConfig
from .storage.azure_blob_store import AzureBlobKVStore
from .storage.azure_table_store import AzureTableMetadataStore

__all__ = [
    'SecureImagePipeline',
    'ImageMetadata',
    'ProcessingResult',
    'AzureStorageConfig',
    'AzureBlobKVStore',
    'AzureTableMetadataStore'
]

__version__ = '3.0.0'  # Updated with FHE_CT storage
