"""
End-to-End Similarity Search Test
==================================
Complete workflow with DeepHash v4.0:
1. Load query images from query_images/
2. Build query requests using query_pipeline (v4.0, no PCA)
3. Send to similarity_search service
4. Decrypt results using retrieval_pipeline
5. Save query + retrieved images side-by-side
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import shutil
import time
from datetime import datetime
from query_pipeline import QueryPipeline
from retrieval_pipeline import RetrievalPipeline
import requests


class EndToEndSearchTest:
    """Complete end-to-end similarity search test (v4.0)."""
    
    def __init__(
        self,
        query_images_dir: str = "query_images",
        output_dir: str = "retrieved_images",
        similarity_service_url: str = "http://localhost:8000/api/v1/search",
        device: str = "cuda"
    ):
        self.query_images_dir = Path(query_images_dir)
        self.output_dir = Path(output_dir)
        self.similarity_service_url = similarity_service_url
        self.device = device
        
        print("\n" + "=" * 80)
        print("END-TO-END SEARCH TEST INITIALIZED (v4.0)")
        print("=" * 80)
        print(f"Query images: {self.query_images_dir}")
        print(f"Output dir: {self.output_dir}")
        print(f"Search service: {self.similarity_service_url}")
        print(f"Device: {device}")
        print("=" * 80)
        
        # Initialize pipelines
        print("\n[Initializing Query Pipeline (v4.0)...]")
        self.query_pipeline = QueryPipeline(
            convnext_model_path='./models/convnextv2_best_phase1.pt',
            deephash_model_path='./models/deephash_v4_state_dict.pt',
            # No pca_transform_path for v4.0!
            device=device
        )
        
        print("\n[Initializing Retrieval Pipeline...]")
        self.retrieval_pipeline = RetrievalPipeline(
            similarity_service_url=similarity_service_url,
            output_dir=str(output_dir)
        )
        
        print("\n" + "=" * 80)
        print("✓ ALL PIPELINES READY (v4.0)")
        print("=" * 80)
    
    def run_single_query(
        self,
        query_image_path: Path,
        top_k: int = 5
    ):
        """Run complete search for a single query image."""
        query_id = query_image_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"{query_id}_{timestamp}"
        
        print("\n" + "=" * 80)
        print(f"QUERY SESSION: {session_id}")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            # Step 1: Prepare query request
            print("\n[STEP 1/4] Preparing query request (v4.0)...")
            step1_start = time.time()
            
            query_request = self.query_pipeline.prepare_query(
                image_path=str(query_image_path),
                top_k=top_k
            )
            
            step1_time = (time.time() - step1_start) * 1000
            print(f"[STEP 1/4] ✓ Query prepared ({step1_time:.0f}ms)")
            
            # Step 2: Send to similarity service
            print("\n[STEP 2/4] Querying similarity search service...")
            step2_start = time.time()
            
            response = requests.post(
                self.similarity_service_url,
                json=query_request,
                timeout=120
            )
            
            response.raise_for_status()
            search_results = response.json()
            step2_time = (time.time() - step2_start) * 1000
            
            if search_results.get('status') != 'success':
                print(f"[ERROR] Search failed: {search_results}")
                return None
            
            results = search_results.get('results', [])
            print(f"[STEP 2/4] ✓ Received {len(results)} results ({step2_time:.0f}ms)")
            print(f"[STEP 2/4] Server processing: {search_results.get('processing_time_ms', 0):.0f}ms")
            
            # Step 3: Decrypt results
            print("\n[STEP 3/4] Decrypting retrieved images...")
            step3_start = time.time()
            
            saved_files = self.retrieval_pipeline.retrieve_from_results(
                search_results=results,
                query_id=session_id,
                query_image_path=str(query_image_path)  # ✅ ADD THIS LINE
            )
            
            step3_time = (time.time() - step3_start) * 1000
            print(f"[STEP 3/4] ✓ Decrypted {len(saved_files)} images ({step3_time:.0f}ms)")
            
            # Step 4: Copy query image to results folder
            print("\n[STEP 4/4] Organizing results...")
            result_dir = self.output_dir / session_id
            result_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy query image
            query_copy_path = result_dir / f"QUERY_{query_image_path.name}"
            shutil.copy(query_image_path, query_copy_path)
            print(f"[STEP 4/4] ✓ Saved query image: {query_copy_path.name}")
            
            # Save query request
            query_request_path = result_dir / "query_request.json"
            with open(query_request_path, 'w') as f:
                json.dump(query_request, f, indent=2)
            print(f"[STEP 4/4] ✓ Saved query request: {query_request_path.name}")
            
            # Save search response
            response_path = result_dir / "search_response.json"
            with open(response_path, 'w') as f:
                json.dump(search_results, f, indent=2)
            print(f"[STEP 4/4] ✓ Saved search response: {response_path.name}")
            
            # Total time
            total_time = (time.time() - start_time) * 1000
            
            # Print summary
            print("\n" + "=" * 80)
            print(f"✅ SESSION COMPLETE: {session_id}")
            print("=" * 80)
            print(f"Query image: {query_image_path.name}")
            print(f"Results retrieved: {len(saved_files)}")
            print(f"Output folder: {result_dir}")
            print("\n⏱️ Timing Breakdown:")
            print(f"  Query prep: {step1_time:>7.0f}ms")
            print(f"  Search:     {step2_time:>7.0f}ms")
            print(f"  Decryption: {step3_time:>7.0f}ms")
            print(f"  Total E2E:  {total_time:>7.0f}ms")
            print("=" * 80)
            
            return {
                'session_id': session_id,
                'query_image': str(query_image_path),
                'results_count': len(saved_files),
                'output_dir': str(result_dir),
                'success': True,
                'timings': {
                    'query_prep_ms': step1_time,
                    'search_ms': step2_time,
                    'decryption_ms': step3_time,
                    'total_ms': total_time
                }
            }
        
        except Exception as e:
            print(f"\n❌ SESSION FAILED: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'session_id': session_id,
                'query_image': str(query_image_path),
                'error': str(e),
                'success': False
            }
    
    def run_all_queries(self, top_k: int = 5):
        """Run search for all images in query_images/ folder."""
        # Find all images
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        query_images = []
        
        for ext in image_extensions:
            query_images.extend(self.query_images_dir.glob(f'*{ext}'))
            query_images.extend(self.query_images_dir.glob(f'*{ext.upper()}'))
        
        query_images = sorted(set(query_images))
        
        if not query_images:
            print(f"[ERROR] No images found in {self.query_images_dir}")
            print("Supported formats: .jpg, .jpeg, .png, .bmp")
            return
        
        print(f"\n📸 Found {len(query_images)} query images")
        
        # Run each query
        results_summary = []
        
        for i, query_image in enumerate(query_images, 1):
            print(f"\n{'=' * 80}")
            print(f"PROCESSING QUERY {i}/{len(query_images)}")
            print(f"{'=' * 80}")
            
            result = self.run_single_query(query_image, top_k=top_k)
            results_summary.append(result)
        
        # Save overall summary
        summary_path = self.output_dir / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, 'w') as f:
            json.dump(results_summary, f, indent=2)
        
        # Print final summary
        print("\n" + "=" * 80)
        print("ALL QUERIES COMPLETED")
        print("=" * 80)
        
        successful = sum(1 for r in results_summary if r.get('success', False))
        failed = len(results_summary) - successful
        
        print(f"Total queries: {len(results_summary)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        # Calculate average timings
        if successful > 0:
            avg_query = sum(r.get('timings', {}).get('query_prep_ms', 0)
                          for r in results_summary if r.get('success')) / successful
            avg_search = sum(r.get('timings', {}).get('search_ms', 0)
                           for r in results_summary if r.get('success')) / successful
            avg_decrypt = sum(r.get('timings', {}).get('decryption_ms', 0)
                            for r in results_summary if r.get('success')) / successful
            avg_total = sum(r.get('timings', {}).get('total_ms', 0)
                          for r in results_summary if r.get('success')) / successful
            
            print("\n⏱️ Average Timings:")
            print(f"  Query prep: {avg_query:>7.0f}ms")
            print(f"  Search:     {avg_search:>7.0f}ms")
            print(f"  Decryption: {avg_decrypt:>7.0f}ms")
            print(f"  Total E2E:  {avg_total:>7.0f}ms")
        
        print(f"\n📄 Summary saved: {summary_path}")
        print("=" * 80)


def main():
    """Run end-to-end search test."""
    import torch
    
    # Auto-detect device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Configuration
    TOP_K = 5  # Number of results per query
    
    # Initialize test
    test = EndToEndSearchTest(
        query_images_dir="query_images",
        output_dir="retrieved_images",
        similarity_service_url="http://localhost:8000/api/v1/search",
        device=device
    )
    
    # Run all queries
    test.run_all_queries(top_k=TOP_K)


if __name__ == "__main__":
    main()
