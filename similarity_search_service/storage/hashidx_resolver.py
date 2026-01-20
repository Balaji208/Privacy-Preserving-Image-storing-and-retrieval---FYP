"""
Hash Index Resolution Module
==============================

Maps candidate hash indices to Azure RowKeys for entity retrieval.

Important:
    hash_idx (from Redis) = SHA-256(image_id || BFV_ciphertext)
    Azure RowKey = same SHA-256 hash (base64url encoded)
    
    This module handles format conversion if needed.
"""

import logging
import hashlib
import base64
from typing import List

logger = logging.getLogger(__name__)


class HashIndexResolver:
    """
    Resolves hash indices to Azure Table Storage RowKeys.
    
    In current design:
        hash_idx (Redis bytes) = RowKey (Azure string)
    
    This module provides conversion utilities if formats differ.
    """
    
    def __init__(self):
        """Initialize resolver."""
        logger.info("Hash index resolver initialized")
    
    def resolve_to_row_keys(self, hash_indices: List[bytes]) -> List[str]:
        """
        Convert hash indices to Azure RowKeys.
        
        Args:
            hash_indices: List of hash indices from Redis (bytes)
        
        Returns:
            List of RowKeys (base64url strings)
        
        Format:
            Redis: raw bytes (32-byte SHA-256)
            Azure: base64url encoded (43-44 chars, no padding)
        """
        row_keys = []
        
        for hash_idx in hash_indices:
            try:
                # Hash index from Redis should already be base64url encoded
                # If stored as bytes, decode to string
                if isinstance(hash_idx, bytes):
                    row_key = hash_idx.decode('utf-8')
                else:
                    row_key = str(hash_idx)
                
                row_keys.append(row_key)
                
            except Exception as e:
                logger.warning(f"Failed to resolve hash index: {e}")
                continue
        
        logger.debug(f"✓ Resolved {len(row_keys)} hash indices to RowKeys")
        return row_keys
    
    def compute_row_key_from_components(
        self,
        image_id: str,
        fhe_ciphertext: bytes
    ) -> str:
        """
        Compute RowKey from image_id and FHE ciphertext.
        
        This matches the storage phase key generation:
            hash_idx = SHA-256(image_id || FHE_ciphertext)
            row_key = base64url(hash_idx)
        
        Args:
            image_id: Image identifier
            fhe_ciphertext: BFV encrypted hash
        
        Returns:
            Base64url encoded RowKey
        """
        # Concatenate image_id + FHE ciphertext
        combined = image_id.encode('utf-8') + fhe_ciphertext
        
        # SHA-256 hash
        hash_digest = hashlib.sha256(combined).digest()
        
        # Base64url encode (no padding)
        row_key = base64.urlsafe_b64encode(hash_digest).decode('utf-8').rstrip('=')
        
        return row_key
