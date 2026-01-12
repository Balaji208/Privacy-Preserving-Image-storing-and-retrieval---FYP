"""
Azure Storage Configuration
============================
Configuration for Azure Table Storage
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AzureStorageConfig:
    """Azure Table Storage configuration."""
    
    # Connection string from Azure Portal
    connection_string: str
    
    # Table name for key-value store
    table_name: str = "kvstore"
    
    # Partition key prefix length (for distribution)
    partition_key_length: int = 4
    
    @classmethod
    def from_env(cls) -> 'AzureStorageConfig':
        """Load configuration from environment variables."""
        conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not conn_str:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING environment variable not set. "
                "Get it from Azure Portal: Storage Account > Access keys"
            )
        
        return cls(
            connection_string=conn_str,
            table_name=os.getenv('AZURE_TABLE_NAME', 'kvstore')
        )
    
    @classmethod
    def from_connection_string(cls, connection_string: str) -> 'AzureStorageConfig':
        """Create config from connection string."""
        return cls(connection_string=connection_string)
