from azure.storage.blob import BlobServiceClient
from typing import List, Dict
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class BlobFetcher:
    """Fetch JSON objects from Azure Blob Storage."""
    
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_client = self.blob_service_client.get_container_client(
            settings.AZURE_CONTAINER_NAME
        )
        logger.info(f"Azure Blob client initialized: container={settings.AZURE_CONTAINER_NAME}")
    
    def batch_fetch_blobs(
        self,
        blob_names: List[str],
        max_workers: int = 20
    ) -> Dict[str, dict]:
        """
        Fetch multiple JSON blobs in parallel.
        
        Args:
            blob_names: List of blob names (WITHOUT .json extension)
            max_workers: Number of parallel threads
        
        Returns:
            Dictionary mapping blob_name to JSON object
        """
        
        logger.info(f"Fetching {len(blob_names)} blobs from Azure (parallel)")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_blob = {
                executor.submit(self._fetch_single_blob, blob_name): blob_name
                for blob_name in blob_names
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_blob):
                blob_name = future_to_blob[future]
                try:
                    json_data = future.result()
                    if json_data:
                        results[blob_name] = json_data
                except Exception as e:
                    logger.warning(f"Failed to fetch blob {blob_name}: {e}")
        
        logger.info(f"Successfully fetched {len(results)}/{len(blob_names)} blobs")
        
        return results
    
    def _fetch_single_blob(self, blob_name: str) -> dict:
        """
        Fetch a single JSON blob from Azure.
        
        Args:
            blob_name: Blob name WITHOUT .json extension
        
        Returns:
            Parsed JSON object
        """
        
        try:
            # Add .json extension for Azure Blob Storage
            blob_name_with_ext = f"{blob_name}.json"
            
            # Download blob
            blob_client = self.container_client.get_blob_client(blob_name_with_ext)
            blob_data = blob_client.download_blob().readall()
            
            # Parse JSON
            json_obj = json.loads(blob_data)
            
            logger.debug(f"Fetched blob: {blob_name_with_ext}")
            
            return json_obj
            
        except Exception as e:
            logger.error(f"Error fetching blob {blob_name}: {e}")
            return None
    
    def extract_fhe_cts(self, blob_data: Dict[str, dict]) -> Dict[str, str]:
        """
        Extract FHE ciphertexts from JSON objects.
        
        Checks multiple possible field names:
        - fhe_ciphertext (your format)
        - fhe_ct_base64
        - query_fhe_hash
        - query_fhe_ct
        
        Args:
            blob_data: Dictionary of blob_name → JSON object
        
        Returns:
            Dictionary of blob_name → fhe_ciphertext_base64
        """
        
        fhe_cts = {}
        
        for blob_name, json_obj in blob_data.items():
            try:
                # Try multiple field names (prioritize most common)
                fhe_ct = (
                    json_obj.get('fhe_ciphertext') or      # ✅ Your field name
                    json_obj.get('fhe_ct_base64') or
                    json_obj.get('query_fhe_hash') or
                    json_obj.get('query_fhe_ct')
                )
                
                if fhe_ct:
                    fhe_cts[blob_name] = fhe_ct
                    logger.debug(f"Extracted FHE CT from {blob_name}")
                else:
                    logger.warning(
                        f"No FHE ciphertext found in blob: {blob_name}. "
                        f"Available fields: {list(json_obj.keys())}"
                    )
                    
            except Exception as e:
                logger.error(f"Error extracting FHE CT from {blob_name}: {e}")
        
        logger.info(f"Extracted {len(fhe_cts)}/{len(blob_data)} FHE ciphertexts")
        
        if len(fhe_cts) == 0 and len(blob_data) > 0:
            # Log first JSON structure for debugging
            first_blob = list(blob_data.keys())[0]
            first_json = blob_data[first_blob]
            logger.error(
                f"No FHE ciphertexts extracted! "
                f"Sample JSON structure from {first_blob}: {list(first_json.keys())}"
            )
        
        return fhe_cts
