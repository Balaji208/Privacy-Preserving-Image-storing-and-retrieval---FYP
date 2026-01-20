"""
fhe/decryption_client.py
=========================

Client for calling external decryption service (with HSM access).
"""

import logging
import requests
import base64
from typing import List, Optional, Tuple
import tenseal as ts

logger = logging.getLogger(__name__)


class DecryptionServiceClient:
    """
    Client for external decryption service.
    
    Architecture:
    - Similarity service (this): Computes encrypted distances
    - Decryption service (external): Decrypts using HSM secret key
    - Secret key never exposed to similarity service
    """
    
    def __init__(self, decryption_service_url: str, api_key: Optional[str] = None):
        """
        Initialize decryption service client.
        
        Args:
            decryption_service_url: URL of decryption service
            api_key: Optional API key for authentication
        """
        self.service_url = decryption_service_url
        self.api_key = api_key
        
        logger.info(f"Decryption client initialized: {decryption_service_url}")
    
    def decrypt_distance(self, encrypted_distance: ts.BFVVector) -> Optional[int]:
        """
        Decrypt single Hamming distance.
        
        Args:
            encrypted_distance: Encrypted distance (scalar ciphertext)
        
        Returns:
            Decrypted Hamming distance (0-256) or None if failed
        """
        try:
            # Serialize ciphertext
            ct_bytes = encrypted_distance.serialize()
            ct_b64 = base64.b64encode(ct_bytes).decode('utf-8')
            
            # Call decryption service
            headers = {}
            if self.api_key:
                headers['Authorization'] = f"Bearer {self.api_key}"
            
            response = requests.post(
                f"{self.service_url}/decrypt",
                json={"ciphertext": ct_b64},
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            
            # Extract distance from first slot
            plaintext = response.json()["plaintext"]
            distance = plaintext[0]  # Distance in first slot after tree reduction
            
            # Validate range
            if not (0 <= distance <= 256):
                logger.warning(f"Invalid distance: {distance}")
                return None
            
            logger.debug(f"✓ Decrypted distance: {distance}")
            return distance
            
        except requests.RequestException as e:
            logger.error(f"Decryption service error: {e}")
            return None
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def decrypt_distances_batch(
        self,
        encrypted_distances: List[Tuple[int, ts.BFVVector]]
    ) -> List[Tuple[int, Optional[int]]]:
        """
        Decrypt multiple distances in batch.
        
        Args:
            encrypted_distances: List of (index, encrypted_distance) tuples
        
        Returns:
            List of (index, decrypted_distance) tuples
        """
        results = []
        
        # Serialize all ciphertexts
        batch_data = []
        for idx, ct in encrypted_distances:
            if ct is None:
                results.append((idx, None))
                continue
            
            ct_bytes = ct.serialize()
            ct_b64 = base64.b64encode(ct_bytes).decode('utf-8')
            batch_data.append({"index": idx, "ciphertext": ct_b64})
        
        try:
            # Batch decrypt call
            headers = {}
            if self.api_key:
                headers['Authorization'] = f"Bearer {self.api_key}"
            
            response = requests.post(
                f"{self.service_url}/decrypt/batch",
                json={"ciphertexts": batch_data},
                headers=headers,
                timeout=60
            )
            
            response.raise_for_status()
            
            # Parse results
            decrypted = response.json()["results"]
            
            for item in decrypted:
                idx = item["index"]
                distance = item["plaintext"][0]  # First slot
                
                if 0 <= distance <= 256:
                    results.append((idx, distance))
                else:
                    results.append((idx, None))
            
            successful = sum(1 for _, d in results if d is not None)
            logger.info(f"✓ Batch decryption: {successful}/{len(results)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch decryption failed: {e}")
            # Return None for all
            return [(idx, None) for idx, _ in encrypted_distances]
