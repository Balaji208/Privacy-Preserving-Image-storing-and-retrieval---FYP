"""
Simple Similarity Search API
=============================
Simplified image similarity search with proper file path resolution.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json
import time
from typing import Dict
from datetime import datetime
import requests


class SimilaritySearchAPI:
    """Simple API for similarity search."""
    
    def __init__(
        self,
        similarity_service_url: str = "http://localhost:8000/api/v1/search",
        output_dir: str = "temp_search_results",
        device: str = "cuda"
    ):
        """Initialize search API."""
        from query_pipeline import QueryPipeline
        from retrieval_pipeline import RetrievalPipeline
        
        self.similarity_service_url = similarity_service_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify model paths
        convnext_path = Path('models/convnextv2_best_phase1.pt')
        deephash_path = Path('models/deephash_v4_state_dict.pt')
        
        print("🔧 Initializing Similarity Search API...")
        
        if convnext_path.exists():
            print(f"  ✓ Found model: {convnext_path.absolute()}")
        else:
            raise FileNotFoundError(f"ConvNeXt model not found: {convnext_path.absolute()}")
        
        if deephash_path.exists():
            print(f"  ✓ Found model: {deephash_path.absolute()}")
        else:
            raise FileNotFoundError(f"DeepHash model not found: {deephash_path.absolute()}")
        
        print(f"📁 ConvNeXt model: {convnext_path.absolute()}")
        print(f"📁 DeepHash model: {deephash_path.absolute()}")
        
        # Initialize pipelines
        self.query_pipeline = QueryPipeline(
            convnext_model_path=str(convnext_path),
            deephash_model_path=str(deephash_path),
            device=device
        )
        
        self.retrieval_pipeline = RetrievalPipeline(
            similarity_service_url=similarity_service_url,
            output_dir=str(output_dir)
        )
        
        print("✅ Search API ready!\n")
    
    def search(
        self,
        query_image_path: str,
        top_k: int = 5,
        save_images: bool = True
    ) -> Dict:
        """Search for similar images."""
        start_time = time.time()
        
        # Generate session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_name = Path(query_image_path).stem
        session_id = f"{query_name}_{timestamp}"
        
        print(f"🔍 Searching for images similar to: {Path(query_image_path).name}")
        print(f"   Top-K: {top_k}")
        print(f"   Session ID: {session_id}\n")
        
        try:
            # Step 1: Prepare query
            print("[1/3] Preparing query...")
            step1_start = time.time()
            
            query_request = self.query_pipeline.prepare_query(
                image_path=query_image_path,
                top_k=top_k
            )
            
            step1_time = (time.time() - step1_start) * 1000
            print(f"      ✓ Query prepared ({step1_time:.0f}ms)\n")
            
            # Step 2: Send to similarity service
            print("[2/3] Querying similarity search service...")
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
                raise Exception(f"Search failed: {search_results.get('message', 'Unknown error')}")
            
            raw_results = search_results.get('results', [])
            print(f"      ✓ Received {len(raw_results)} results ({step2_time:.0f}ms)\n")
            
            # Step 3: Decrypt and save images
            step3_start = time.time()
            session_dir = None
            
            if save_images and raw_results:
                print("[3/3] Decrypting and saving images...")
                
                # Call retrieval pipeline
                self.retrieval_pipeline.retrieve_from_results(
                    search_results=raw_results,
                    query_id=session_id,
                    query_image_path=query_image_path
                )
                
                # Get session directory
                session_dir = self.output_dir / session_id
                
                step3_time = (time.time() - step3_start) * 1000
                print(f"      ✓ Saved {len(raw_results)} images ({step3_time:.0f}ms)\n")
            else:
                step3_time = 0
                print("[3/3] Skipping image save (save_images=False)\n")
            
            # Format results with correct file paths
            formatted_results = []
            
            for i, result in enumerate(raw_results):
                image_id = result.get('image_id', f'unknown_{i}')
                blob_name = result.get('blob_name', '')
                
                # Extract image name from blob_name
                if blob_name:
                    # blob_name format: "encrypted/tenant_id/image_hash.enc"
                    # Extract just the filename part
                    image_name = blob_name.split('/')[-1]
                    if image_name.endswith('.enc'):
                        image_name = image_name[:-4] + '.jpg'  # Remove .enc and add .jpg
                else:
                    image_name = f"{image_id}.jpg"
                
                # ✅ FIX: Look for saved files in session directory
                image_path = None
                if save_images and session_dir and session_dir.exists():
                    # List all files in session directory
                    all_files = list(session_dir.glob("*.jpg"))
                    
                    # Filter out QUERY file and collage
                    result_files = [f for f in all_files 
                                   if not f.name.startswith('QUERY') 
                                   and not f.name.startswith('collage')]
                    
                    # Match by position (sorted alphabetically)
                    if i < len(result_files):
                        # Sort files to ensure consistent ordering
                        result_files.sort()
                        image_path = str(result_files[i])
                
                formatted_results.append({
                    'rank': i + 1,
                    'image_id': image_id,
                    'image_name': image_name,
                    'similarity': result.get('similarity_score', 0.0),
                    'hamming_distance': result.get('hamming_distance', 0),
                    'image_path': image_path,
                    'metadata': result.get('metadata', {})
                })
            
            total_time = (time.time() - start_time) * 1000
            
            # Print summary
            print("=" * 60)
            print(f"✅ Search Complete!")
            print("=" * 60)
            print(f"Query: {Path(query_image_path).name}")
            print(f"Results found: {len(formatted_results)}")
            
            if formatted_results:
                print(f"\nTop Results:")
                for result in formatted_results[:3]:
                    print(f"  #{result['rank']}: {result['image_name']}")
                    print(f"           Similarity: {result['similarity']:.2%}")
                    print(f"           Hamming: {result['hamming_distance']}/256 bits")
                    if result['image_path']:
                        print(f"           Saved: {Path(result['image_path']).name}")
            
            print(f"\n⏱️  Total time: {total_time:.0f}ms")
            print("=" * 60 + "\n")
            
            return {
                'success': True,
                'session_id': session_id,
                'query_image': query_image_path,
                'results': formatted_results,
                'timings': {
                    'query_prep_ms': step1_time,
                    'search_ms': step2_time,
                    'decryption_ms': step3_time,
                    'total_ms': total_time
                }
            }
            
        except Exception as e:
            print(f"\n❌ Search failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'session_id': session_id,
                'query_image': query_image_path,
                'error': str(e),
                'results': []
            }
