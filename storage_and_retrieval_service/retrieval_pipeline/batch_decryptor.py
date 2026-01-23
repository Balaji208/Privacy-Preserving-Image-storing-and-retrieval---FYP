"""
Batch Image Decryptor
=====================
Decrypts multiple images in parallel using image_encryption module.
"""

from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from image_encryption.image_decryptor import ImageDecryptor
import time


class BatchDecryptor:
    """Decrypt multiple images in parallel."""
    
    def __init__(self):
        self.decryptor = ImageDecryptor()
        print("[BatchDecryptor] Initialized with HSM decryption support")
    
    def decrypt_images(
        self,
        search_results: List[Dict],
        max_workers: int = 4  # HSM operations are thread-safe but limited
    ) -> List[Tuple[bytes, Dict]]:
        """
        Decrypt multiple images in parallel.
        
        Args:
            search_results: List of search results from similarity service
                Each result contains complete encrypted image data in metadata
            max_workers: Number of parallel decryption threads
                Note: Keep this low (4-8) for HSM operations
        
        Returns:
            List of (decrypted_image_bytes, metadata) tuples
        """
        # ✅ FIX: Handle empty search results
        if not search_results:
            print("[BatchDecryptor] No search results to decrypt")
            return []
        
        print(f"\n[BatchDecryptor] Decrypting {len(search_results)} images...")
        print(f"[BatchDecryptor] Using {max_workers} parallel workers")
        
        start_time = time.time()
        decrypted_images = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all decryption tasks
            future_to_result = {
                executor.submit(
                    self._decrypt_single_image,
                    result
                ): result
                for result in search_results
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_result):
                result = future_to_result[future]
                try:
                    decrypted_bytes, metadata = future.result()
                    if decrypted_bytes:
                        decrypted_images.append((decrypted_bytes, metadata))
                except Exception as e:
                    image_id = result.get('metadata', {}).get('image_id', 'unknown')
                    print(f"[ERROR] Failed to decrypt image {image_id}: {e}")
        
        elapsed = time.time() - start_time
        
        print(f"[BatchDecryptor] ✓ Decrypted {len(decrypted_images)}/{len(search_results)} images")
        
        # ✅ FIX: Only calculate per-image time if we have results
        if len(search_results) > 0:
            avg_time = elapsed / len(search_results)
            print(f"[BatchDecryptor] Total time: {elapsed:.2f}s ({avg_time:.2f}s per image)")
        else:
            print(f"[BatchDecryptor] Total time: {elapsed:.2f}s")
        
        return decrypted_images
    
    def _decrypt_single_image(
        self,
        search_result: Dict
    ) -> Tuple[bytes, Dict]:
        """
        Decrypt a single image from search result.
        
        Args:
            search_result: Single search result containing:
                - blob_name: Blob identifier
                - rank: Search rank
                - encrypted_distance: Encrypted similarity distance
                - metadata: Complete encrypted image data
        
        Returns:
            (decrypted_image_bytes, metadata)
        """
        try:
            rank = search_result.get('rank', 0)
            metadata = search_result.get('metadata', {})
            image_id = metadata.get('image_id', 'unknown')
            
            print(f"[Decrypt] Rank {rank}: {image_id}...")
            
            # The metadata already contains all encrypted fields
            # No need to fetch from Azure!
            encrypted_obj = metadata
            
            # Decrypt using ImageDecryptor
            decrypted_bytes = self.decryptor.decrypt_image(encrypted_obj)
            
            # Add search metadata
            metadata['search_rank'] = rank
            metadata['encrypted_distance'] = search_result.get('encrypted_distance')
            metadata['blob_name'] = search_result.get('blob_name')
            
            print(f"[Decrypt] ✓ Rank {rank}: {len(decrypted_bytes):,} bytes")
            
            return decrypted_bytes, metadata
        
        except Exception as e:
            print(f"[ERROR] Decryption failed for rank {rank}: {e}")
            raise
