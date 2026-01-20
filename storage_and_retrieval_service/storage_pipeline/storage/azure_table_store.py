"""
Azure Table Storage Metadata Index (Optional)
==============================================

Provides fast lookups without scanning Blob Storage.

Schema:
  PartitionKey: HMAC(FHE_CT || image_id)[:4]
  RowKey: HMAC(FHE_CT || image_id) [64 chars]
  blob_name: Reference to blob in Blob Storage
  image_id: For quick lookup
  size: Blob size
  timestamp: Upload time
"""

import hashlib
import hmac
import logging
from typing import Dict, Optional, List
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class AzureTableMetadataStore:
    """Azure Table Storage for metadata indexing (optional)."""
    
    def __init__(
        self,
        connection_string: str,
        hmac_key: bytes,
        partition_key_length: int = 4,
        table_name: str = "imagemetadata"
    ):
        """
        Initialize Azure Table Storage for metadata.
        
        Args:
            connection_string: Azure Storage connection string
            hmac_key: 32-byte HMAC key (same as blob store)
            partition_key_length: Partition key prefix length
            table_name: Azure table name
        """
        self.connection_string = connection_string
        self.hmac_key = hmac_key
        self.partition_key_length = partition_key_length
        self.table_name = table_name
        
        # Validate HMAC key
        if len(hmac_key) != 32:
            raise ValueError(f"HMAC key must be 32 bytes, got {len(hmac_key)}")
        
        # Initialize Azure clients
        self.service_client = TableServiceClient.from_connection_string(connection_string)
        self.table_client = self._get_or_create_table()
        
        logger.info(f"✓ Azure Table metadata store initialized (table: {table_name})")
    
    def _get_or_create_table(self) -> TableClient:
        """Create table if not exists."""
        try:
            self.service_client.create_table(self.table_name)
            logger.info(f"✓ Created table: {self.table_name}")
        except ResourceExistsError:
            logger.info(f"✓ Using existing table: {self.table_name}")
        
        return self.service_client.get_table_client(self.table_name)
    
    def _compute_hmac_token(self, fhe_ciphertext: bytes, image_id: str) -> str:
        """Compute HMAC token (same as blob store)."""
        image_id_bytes = image_id.encode('utf-8')
        message = fhe_ciphertext + image_id_bytes
        
        h = hmac.new(
            self.hmac_key,
            message,
            hashlib.sha3_256
        )
        
        return h.hexdigest()
    
    def put(
        self,
        fhe_ciphertext: bytes,
        image_id: str,
        blob_name: str,
        blob_size: int
    ) -> None:
        """
        Store metadata entry.
        
        Args:
            fhe_ciphertext: FHE ciphertext (for key generation)
            image_id: Image identifier
            blob_name: Reference to blob
            blob_size: Size of blob in bytes
        """
        hmac_token = self._compute_hmac_token(fhe_ciphertext, image_id)
        partition_key = hmac_token[:self.partition_key_length]
        row_key = hmac_token
        
        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "blob_name": blob_name,
            "image_id": image_id,
            "blob_size": blob_size
        }
        
        try:
            self.table_client.upsert_entity(entity)
            logger.debug(f"✓ Metadata stored: PK={partition_key}, image_id={image_id}")
        except Exception as e:
            logger.error(f"Failed to store metadata: {e}")
    
    def get(
        self,
        fhe_ciphertext: bytes,
        image_id: str
    ) -> Optional[Dict]:
        """Retrieve metadata by FHE ciphertext and image_id."""
        hmac_token = self._compute_hmac_token(fhe_ciphertext, image_id)
        partition_key = hmac_token[:self.partition_key_length]
        row_key = hmac_token
        
        try:
            entity = self.table_client.get_entity(partition_key, row_key)
            return {
                'blob_name': entity['blob_name'],
                'image_id': entity['image_id'],
                'blob_size': entity['blob_size']
            }
        except ResourceNotFoundError:
            return None
    
    def get_by_image_id(self, image_id: str) -> Optional[Dict]:
        """Retrieve metadata by image_id (table scan)."""
        try:
            query_filter = f"image_id eq '{image_id}'"
            entities = self.table_client.query_entities(query_filter)
            
            for entity in entities:
                return {
                    'blob_name': entity['blob_name'],
                    'image_id': entity['image_id'],
                    'blob_size': entity['blob_size'],
                    'row_key': entity['RowKey']
                }
            
            return None
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None
