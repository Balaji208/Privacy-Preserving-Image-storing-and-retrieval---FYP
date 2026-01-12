"""
Azure Table Storage KV Store - MINIMAL Schema (Base64URL safe)
=============================================================
PartitionKey | RowKey | json_data  ← ONLY 3 columns!
RowKey: base64url (no / + = chars)
"""

import base64
import json
import hashlib
import logging
import urllib.parse
from typing import Dict, Optional, Tuple
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

logger = logging.getLogger(__name__)

class AzureTableKVStore:
    def __init__(self, connection_string: str, partition_key_length: int = 4):
        self.connection_string = connection_string
        self.partition_key_length = partition_key_length
        
        self.service_client = TableServiceClient.from_connection_string(connection_string)
        self.table_client = self._get_or_create_table()
        logger.info("✓ Azure Table Storage (minimal schema) initialized")
    
    def _get_or_create_table(self) -> TableClient:
        try:
            self.service_client.create_table("fhekvstore")
            logger.info("✓ Created table: fhekvstore")
        except ResourceExistsError:
            logger.info("✓ Using existing table: fhekvstore")
        return self.service_client.get_table_client("fhekvstore")
    
    def _base64url_encode(self, data: bytes) -> str:
        """Azure-safe base64url (no / + =)"""
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')
    
    def _compute_storage_keys(self, fhe_ciphertext: bytes) -> Tuple[str, str]:
        # SHA256 → base64url (Azure-safe)
        sha256_hash = hashlib.sha256(fhe_ciphertext).digest()
        row_key = self._base64url_encode(sha256_hash)
        partition_key = row_key[:self.partition_key_length]
        return partition_key, row_key
    
    def put(self, fhe_ciphertext: bytes, **kwargs) -> Tuple[str, str]:
        """ONLY 3 columns: PartitionKey | RowKey | json_data"""
        encryption_json = kwargs.get('value') or kwargs.get('encryption_json')
        if not encryption_json:
            raise ValueError("Missing encryption_json")
        
        partition_key, row_key = self._compute_storage_keys(fhe_ciphertext)
        
        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "json_data": json.dumps(encryption_json)
        }
        
        try:
            self.table_client.create_entity(entity)
            logger.info(f"✓ Stored: PK={partition_key}, RK={row_key}")
        except Exception as e:
            logger.warning(f"Create failed, trying upsert: {e}")
            self.table_client.upsert_entity(entity)
            logger.info(f"✓ Stored (upsert): PK={partition_key}, RK={row_key}")
        
        return partition_key, row_key
    
    def get(self, fhe_ciphertext: bytes) -> Optional[Dict]:
        partition_key, row_key = self._compute_storage_keys(fhe_ciphertext)
        try:
            entity = self.table_client.get_entity(partition_key, row_key)
            return {'value': json.loads(entity['json_data'])}
        except ResourceNotFoundError:
            return None
    
    def get_by_row_key(self, row_key: str) -> Optional[Dict]:
        partition_key = row_key[:self.partition_key_length]
        try:
            entity = self.table_client.get_entity(partition_key, row_key)
            return {'value': json.loads(entity['json_data'])}
        except ResourceNotFoundError:
            return None
    
    def get_by_image_id(self, image_id: str) -> Optional[Dict]:
        """Scan json_data for image_id in metadata"""
        try:
            for entity in self.table_client.list_entities():
                json_data = json.loads(entity['json_data'])
                if json_data.get('metadata', {}).get('image_id') == image_id:
                    return {
                        'value': json_data,
                        'row_key': entity['RowKey']
                    }
            return None
        except:
            return None
    
    def count_entities(self) -> int:
        return sum(1 for _ in self.table_client.list_entities())
    
    def list_image_ids(self, max_results: int = 100) -> list:
        result = []
        for entity in self.table_client.list_entities(results_per_page=max_results):
            try:
                image_id = json.loads(entity['json_data'])['metadata']['image_id']
                result.append({"image_id": image_id, "row_key": entity['RowKey']})
            except:
                continue
        return result
