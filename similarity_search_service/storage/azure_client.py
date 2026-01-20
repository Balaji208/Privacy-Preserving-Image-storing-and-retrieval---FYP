"""
Azure Table Storage Client
===========================

Retrieves encrypted image data from Azure Table Storage using hash indices.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from azure.data.tables.aio import TableServiceClient, TableClient
from azure.core.exceptions import ResourceNotFoundError, AzureError

from config.settings import Settings

logger = logging.getLogger(__name__)


class AzureTableClient:
    """
    Async Azure Table Storage client for encrypted image retrieval.
    
    Schema:
        PartitionKey: First 4 chars of RowKey
        RowKey: SHA-256(image_id || BFV_ciphertext) base64url encoded
        json_data: Encrypted image + metadata JSON
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize Azure Table client.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.service_client: Optional[TableServiceClient] = None
        self.table_client: Optional[TableClient] = None
        self._initialized = False
        
        logger.info(
            f"Azure Table client configured: "
            f"table={settings.azure_table_name}"
        )
    
    async def initialize(self):
        """Initialize Azure Table Storage connection."""
        if self._initialized:
            return
        
        try:
            self.service_client = TableServiceClient.from_connection_string(
                self.settings.azure_connection_string
            )
            
            self.table_client = self.service_client.get_table_client(
                self.settings.azure_table_name
            )
            
            self._initialized = True
            logger.info("✓ Azure Table Storage client initialized")
            
        except Exception as e:
            logger.error(f"✗ Azure initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize Azure client: {e}")
    
    async def close(self):
        """Close Azure connections."""
        if self.table_client:
            await self.table_client.close()
        if self.service_client:
            await self.service_client.close()
        
        self._initialized = False
        logger.info("✓ Azure Table Storage client closed")
    
    async def get_by_row_key(self, row_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve entity by RowKey.
        
        Args:
            row_key: Base64url-encoded SHA-256 hash index
        
        Returns:
            Entity data or None if not found
        """
        if not self._initialized:
            raise RuntimeError("Azure client not initialized")
        
        try:
            # PartitionKey = first 4 chars of RowKey
            partition_key = row_key[:4]
            
            entity = await self.table_client.get_entity(
                partition_key=partition_key,
                row_key=row_key
            )
            
            logger.debug(f"✓ Retrieved entity: {row_key[:16]}...")
            return dict(entity)
            
        except ResourceNotFoundError:
            logger.warning(f"Entity not found: {row_key[:16]}...")
            return None
        except AzureError as e:
            logger.error(f"Azure error retrieving {row_key[:16]}...: {e}")
            return None
    
    async def get_batch(
        self,
        row_keys: list[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Retrieve multiple entities concurrently.
        
        Args:
            row_keys: List of RowKeys
        
        Returns:
            Dictionary mapping row_key → entity_data
        """
        if not self._initialized:
            raise RuntimeError("Azure client not initialized")
        
        logger.info(f"Retrieving {len(row_keys)} entities from Azure...")
        
        # Concurrent lookups
        tasks = [self.get_by_row_key(rk) for rk in row_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result map
        result_map = {}
        for row_key, result in zip(row_keys, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to retrieve {row_key[:16]}...: {result}")
                result_map[row_key] = None
            else:
                result_map[row_key] = result
        
        successful = sum(1 for v in result_map.values() if v is not None)
        logger.info(
            f"✓ Retrieved {successful}/{len(row_keys)} entities from Azure"
        )
        
        return result_map
    
    async def health_check(self) -> bool:
        """
        Check Azure connectivity.
        
        Returns:
            True if Azure is reachable
        """
        try:
            if not self._initialized:
                return False
            
            # Simple query to test connection
            query_filter = "PartitionKey ne ''"
            entities = self.table_client.query_entities(
                query_filter=query_filter,
                results_per_page=1
            )
            
            # Consume one result
            async for _ in entities:
                break
            
            return True
        except Exception:
            return False
