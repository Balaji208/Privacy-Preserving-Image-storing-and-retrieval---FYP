"""
Azure Blob Storage for Large Encrypted Images
==============================================

Stores large encryption JSON objects (~1MB+) as blobs.
Uses HMAC(FHE_CT || image_id) as blob name for deterministic access.

Architecture:
  Container: encrypted-images
  Blob Name: HMAC(FHE_CT || image_id).json
  Content: {
    ...encryption_json from image_encryption,
    "fhe_ciphertext": "base64_encoded_fhe_ct"  ← ADDED!
  }
"""

import json
import base64
import hashlib
import hmac
import logging
from typing import Dict, Optional, List
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class AzureBlobKVStore:
    """Azure Blob Storage with HMAC-based blob names + FHE_CT storage."""
    
    def __init__(
        self,
        connection_string: str,
        hmac_key: bytes,
        container_name: str = "encrypted-images"
    ):
        """
        Initialize Azure Blob Storage.
        
        Args:
            connection_string: Azure Storage connection string
            hmac_key: 32-byte HMAC key (from HSM)
            container_name: Blob container name
        """
        self.connection_string = connection_string
        self.hmac_key = hmac_key
        self.container_name = container_name
        
        # Validate HMAC key
        if len(hmac_key) != 32:
            raise ValueError(f"HMAC key must be 32 bytes, got {len(hmac_key)}")
        
        # Initialize Azure clients
        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        self.container_client = self._get_or_create_container()
        
        logger.info(f"✓ Azure Blob Storage initialized (container: {container_name})")
    
    def _get_or_create_container(self) -> ContainerClient:
        """Create container if not exists."""
        try:
            self.blob_service_client.create_container(self.container_name)
            logger.info(f"✓ Created container: {self.container_name}")
        except ResourceExistsError:
            logger.info(f"✓ Using existing container: {self.container_name}")
        
        return self.blob_service_client.get_container_client(self.container_name)
    
    def _compute_hmac_token(self, fhe_ciphertext: bytes, image_id: str) -> str:
        """
        Compute HMAC token: HMAC-SHA3-256(fhe_ct || image_id).
        
        Args:
            fhe_ciphertext: FHE ciphertext bytes (~432KB)
            image_id: Image identifier (salt)
        
        Returns:
            64-character hex-encoded HMAC token
        """
        # Construct message: fhe_ct || image_id
        image_id_bytes = image_id.encode('utf-8')
        message = fhe_ciphertext + image_id_bytes
        
        # Compute HMAC-SHA3-256
        h = hmac.new(
            self.hmac_key,
            message,
            hashlib.sha3_256
        )
        
        token = h.hexdigest()
        logger.debug(f"HMAC token: {token[:16]}... (image_id={image_id})")
        
        return token
    
    def _compute_blob_name(
        self,
        fhe_ciphertext: bytes,
        image_id: str
    ) -> str:
        """
        Compute blob name from HMAC token.
        
        Args:
            fhe_ciphertext: FHE ciphertext
            image_id: Image ID (used as salt)
        
        Returns:
            Blob name: HMAC(FHE_CT || image_id).json
        """
        hmac_token = self._compute_hmac_token(fhe_ciphertext, image_id)
        return f"{hmac_token}.json"
    
    def put(
        self,
        fhe_ciphertext: bytes,
        image_id: str,
        encryption_json: Dict
    ) -> str:
        """
        Store encrypted image data as blob with FHE_CT included.
        
        Args:
            fhe_ciphertext: FHE encrypted hash (~432KB)
            image_id: Image identifier
            encryption_json: Output from image_encryption module
        
        Returns:
            Blob name (HMAC token)
        
        Storage Format:
            {
                ...encryption_json fields,
                "fhe_ciphertext": "base64_encoded_fhe_ct",  ← ADDED
                "fhe_ciphertext_size": 432154
            }
        """
        # Compute blob name
        blob_name = self._compute_blob_name(fhe_ciphertext, image_id)
        
        # ✅ ADD FHE_CT to JSON
        storage_json = encryption_json.copy()
        storage_json['fhe_ciphertext'] = base64.b64encode(fhe_ciphertext).decode('utf-8')
        storage_json['fhe_ciphertext_size'] = len(fhe_ciphertext)
        
        # Serialize JSON
        json_data = json.dumps(storage_json, indent=2)
        json_bytes = json_data.encode('utf-8')
        
        # Upload to blob
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            blob_client.upload_blob(
                json_bytes,
                overwrite=True,
                metadata={
                    'image_id': image_id,
                    'content_type': 'application/json',
                    'fhe_ct_size': str(len(fhe_ciphertext))
                }
            )
            logger.info(
                f"✓ Stored blob: {blob_name[:32]}... "
                f"({len(json_bytes):,} bytes, includes FHE_CT)"
            )
        except Exception as e:
            logger.error(f"Failed to upload blob: {e}")
            raise
        
        return blob_name
    
    def get(
        self,
        fhe_ciphertext: bytes,
        image_id: str
    ) -> Optional[Dict]:
        """
        Retrieve encrypted image data by FHE ciphertext and image_id.
        
        Args:
            fhe_ciphertext: FHE ciphertext
            image_id: Image ID
        
        Returns:
            Dict with:
                'value': encryption_json (without fhe_ciphertext field)
                'fhe_ciphertext': bytes (extracted FHE CT)
                'blob_name': str
        """
        blob_name = self._compute_blob_name(fhe_ciphertext, image_id)
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            # Download blob
            blob_data = blob_client.download_blob()
            json_bytes = blob_data.readall()
            
            # Parse JSON
            storage_json = json.loads(json_bytes.decode('utf-8'))
            
            # ✅ EXTRACT FHE_CT from JSON
            fhe_ct_base64 = storage_json.pop('fhe_ciphertext', None)
            storage_json.pop('fhe_ciphertext_size', None)
            
            fhe_ct_bytes = None
            if fhe_ct_base64:
                fhe_ct_bytes = base64.b64decode(fhe_ct_base64)
            
            logger.debug(
                f"✓ Retrieved blob: {blob_name[:32]}... "
                f"(FHE CT: {len(fhe_ct_bytes):,} bytes)" if fhe_ct_bytes else ""
            )
            
            return {
                'value': storage_json,  # Original encryption_json
                'fhe_ciphertext': fhe_ct_bytes,  # Extracted FHE CT
                'blob_name': blob_name
            }
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name[:32]}...")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve blob: {e}")
            return None
    
    def get_by_blob_name(self, blob_name: str) -> Optional[Dict]:
        """
        Retrieve by blob name (HMAC token).
        
        Args:
            blob_name: Blob name (64-char HMAC token + .json)
        
        Returns:
            Dict with 'value', 'fhe_ciphertext', 'blob_name' or None
        """
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            blob_data = blob_client.download_blob()
            json_bytes = blob_data.readall()
            storage_json = json.loads(json_bytes.decode('utf-8'))
            
            # Extract FHE_CT
            fhe_ct_base64 = storage_json.pop('fhe_ciphertext', None)
            storage_json.pop('fhe_ciphertext_size', None)
            
            fhe_ct_bytes = None
            if fhe_ct_base64:
                fhe_ct_bytes = base64.b64decode(fhe_ct_base64)
            
            return {
                'value': storage_json,
                'fhe_ciphertext': fhe_ct_bytes,
                'blob_name': blob_name
            }
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name[:32]}...")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve blob: {e}")
            return None
    
    def get_by_image_id(self, image_id: str) -> Optional[Dict]:
        """
        Retrieve by image_id (searches blob metadata).
        
        Args:
            image_id: Image identifier
        
        Returns:
            Dict with 'value', 'fhe_ciphertext', 'blob_name' or None
        
        Warning:
            This searches all blobs - use sparingly!
        """
        try:
            # List all blobs and check metadata
            for blob in self.container_client.list_blobs(include=['metadata']):
                if blob.metadata and blob.metadata.get('image_id') == image_id:
                    # Found matching blob
                    return self.get_by_blob_name(blob.name)
            
            logger.warning(f"Image ID not found: {image_id}")
            return None
            
        except Exception as e:
            logger.error(f"Blob search failed: {e}")
            return None
    
    def list_blobs(self, max_results: int = 100) -> List[Dict]:
        """
        List stored blobs.
        
        Args:
            max_results: Maximum results to return
        
        Returns:
            List of dicts with 'blob_name', 'image_id', 'size'
        """
        result = []
        try:
            for blob in self.container_client.list_blobs(
                include=['metadata'],
                results_per_page=max_results
            ):
                result.append({
                    'blob_name': blob.name,
                    'image_id': blob.metadata.get('image_id', 'unknown'),
                    'size': blob.size,
                    'last_modified': blob.last_modified
                })
            
            return result
        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            return []
    
    def delete(self, fhe_ciphertext: bytes, image_id: str) -> bool:
        """
        Delete blob by FHE ciphertext and image_id.
        
        Args:
            fhe_ciphertext: FHE ciphertext
            image_id: Image ID
        
        Returns:
            True if deleted, False otherwise
        """
        blob_name = self._compute_blob_name(fhe_ciphertext, image_id)
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            blob_client.delete_blob()
            logger.info(f"✓ Deleted blob: {blob_name[:32]}...")
            return True
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_name[:32]}...")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob: {e}")
            return False
    
    def count_blobs(self) -> int:
        """Count total blobs in container."""
        try:
            return sum(1 for _ in self.container_client.list_blobs())
        except Exception as e:
            logger.error(f"Failed to count blobs: {e}")
            return 0
