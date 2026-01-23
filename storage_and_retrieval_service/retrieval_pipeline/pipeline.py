"""
Retrieval Pipeline
==================

Main orchestrator for retrieving and decrypting images from similarity search.
"""

from typing import List, Dict
import requests
import json
import time
from .batch_decryptor import BatchDecryptor
from .image_saver import ImageSaver


class RetrievalPipeline:
    """
    End-to-end retrieval pipeline.
    
    Flow:
    1. Send query to similarity search service
    2. Receive search results (complete JSON with encrypted data)
    3. Decrypt images using Kyber + AES-GCM
    4. Save decrypted images to filesystem
    """
    
    def __init__(
        self,
        similarity_service_url: str = "http://localhost:8000/api/v1/search",
        output_dir: str = "retrieved_images"
    ):
        self.similarity_service_url = similarity_service_url
        self.batch_decryptor = BatchDecryptor()
        self.image_saver = ImageSaver(output_dir)
        
        print("=" * 80)
        print("RETRIEVAL PIPELINE INITIALIZED")
        print("=" * 80)
        print(f"Similarity Service: {similarity_service_url}")
        print(f"Output Directory: {output_dir}")
        print("=" * 80)
    
    def retrieve_and_decrypt(
        self,
        query_request: Dict,
        query_id: str = None
    ) -> List[Dict]:
        """
        Execute full retrieval pipeline.
        
        Args:
            query_request: Search request to send to similarity service
                {
                    "tokens": [...],
                    "query_fhe_ct": "...",
                    "top_k": 5,
                    "tenant_id": "user_001"
                }
            query_id: Optional query identifier
        
        Returns:
            List of saved file information
        """
        
        start_time = time.time()
        
        print("\n" + "=" * 80)
        print("STARTING RETRIEVAL PIPELINE")
        print("=" * 80)
        
        # Step 1: Query similarity search service
        print("\n[STEP 1/4] Querying similarity search service...")
        search_results = self._query_similarity_service(query_request)
        
        if not search_results:
            print("[ERROR] No results from similarity search service")
            return []
        
        print(f"[STEP 1/4] ✓ Received {len(search_results)} search results")
        
        # Step 2: Decrypt images (data already in search results!)
        print("\n[STEP 2/4] Decrypting images...")
        decrypted_images = self.batch_decryptor.decrypt_images(search_results)
        
        if not decrypted_images:
            print("[ERROR] No images successfully decrypted")
            return []
        
        print(f"[STEP 2/4] ✓ Decrypted {len(decrypted_images)} images")
        
        # Step 3: Save images
        print("\n[STEP 3/4] Saving images to filesystem...")
        saved_files = self.image_saver.save_images(decrypted_images, query_id)
        
        print(f"[STEP 3/4] ✓ Saved {len(saved_files)} images")
        
        # Step 4: Print summary
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("RETRIEVAL PIPELINE COMPLETED")
        print("=" * 80)
        print(f"Total time: {elapsed:.2f}s")
        print(f"Images retrieved: {len(saved_files)}")
        print(f"Success rate: {len(saved_files)}/{len(search_results)} ({len(saved_files)/len(search_results)*100:.1f}%)")
        print("=" * 80)
        
        return saved_files
    
    def retrieve_from_results(
    self,
    search_results: List[Dict],
    query_id: str = None,
    query_image_path: str = None  # ✅ NEW PARAMETER
) -> List[Dict]:
        """
        Decrypt and save images from pre-fetched search results.
        
        Args:
            search_results: List of search results from similarity service
            query_id: Optional query identifier
            query_image_path: Path to original query image (for collage)
        
        Returns:
            List of saved file information
        """
        start_time = time.time()
        
        print("\n" + "=" * 80)
        print("RETRIEVAL FROM EXISTING RESULTS")
        print("=" * 80)
        print(f"Input: {len(search_results)} search results")
        
        # Step 1: Decrypt images
        print("\n[STEP 1/2] Decrypting images...")
        decrypted_images = self.batch_decryptor.decrypt_images(search_results)
        
        if not decrypted_images:
            print("[ERROR] No images successfully decrypted")
            return []
        
        print(f"[STEP 1/2] ✓ Decrypted {len(decrypted_images)} images")
        
        # Step 2: Save images with collage
        print("\n[STEP 2/2] Saving images to filesystem...")
        saved_files = self.image_saver.save_images(
            decrypted_images, 
            query_id,
            query_image_path=query_image_path,  # ✅ PASS QUERY PATH
            create_collage=True
        )
        print(f"[STEP 2/2] ✓ Saved {len(saved_files)} images")
        
        # Summary
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("RETRIEVAL COMPLETED")
        print("=" * 80)
        print(f"Total time: {elapsed:.2f}s")
        print(f"Images retrieved: {len(saved_files)}")
        print("=" * 80)
        
        return saved_files

    def _query_similarity_service(self, query_request: Dict) -> List[Dict]:
        """
        Send query to similarity search service.
        
        Returns:
            List of search results (each contains complete encrypted data)
        """
        
        try:
            print(f"[HTTP] POST {self.similarity_service_url}")
            print(f"[HTTP] Request: top_k={query_request.get('top_k')}, tenant={query_request.get('tenant_id')}")
            
            response = requests.post(
                self.similarity_service_url,
                json=query_request,
                timeout=60  # 60 second timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') != 'success':
                print(f"[ERROR] Search service returned error: {result}")
                return []
            
            results = result.get('results', [])
            
            print(f"[HTTP] ✓ Status: {response.status_code}")
            print(f"[HTTP] ✓ Results: {len(results)}")
            print(f"[HTTP] ✓ Processing time: {result.get('processing_time_ms', 0):.0f}ms")
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to query similarity service: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return []
