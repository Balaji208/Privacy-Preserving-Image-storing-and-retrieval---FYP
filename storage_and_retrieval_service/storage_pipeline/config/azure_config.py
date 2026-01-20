"""
Azure Storage Configuration
============================

Configuration for Azure Blob Storage
"""

import os
from dataclasses import dataclass

@dataclass
class AzureStorageConfig:
    """Azure Blob Storage configuration."""

    # Connection string from Azure Portal
    connection_string: str

    # Container name for encrypted images
    container_name: str = "encrypted-images"

    @classmethod
    def from_env(cls) -> 'AzureStorageConfig':
        """Load configuration from environment variables."""
        conn_str = (
            os.getenv('AZURE_STORAGE_CONNECTION_STRING') or
            os.getenv('AZURE_BLOB_STORAGE_CONNECTION_STRING') or
            os.getenv('AZURE_TABLE_STORAGE_CONNECTION_STRING')
        )

        if not conn_str:
            raise ValueError(
                "Azure connection string not set. "
                "Expected one of: AZURE_STORAGE_CONNECTION_STRING, "
                "AZURE_BLOB_STORAGE_CONNECTION_STRING, "
                "AZURE_TABLE_STORAGE_CONNECTION_STRING"
            )

        return cls(
            connection_string=conn_str,
            container_name=os.getenv('AZURE_CONTAINER_NAME', 'encrypted-images')
        )

    @classmethod
    def from_connection_string(
        cls, 
        connection_string: str,
        container_name: str = "encrypted-images"
    ) -> 'AzureStorageConfig':
        """Create config from connection string."""
        return cls(
            connection_string=connection_string,
            container_name=container_name
        )