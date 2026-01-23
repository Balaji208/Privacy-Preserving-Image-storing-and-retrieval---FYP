"""
Test Retrieval Pipeline
=======================

Tests the complete retrieval and decryption workflow.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from retrieval_pipeline import RetrievalPipeline


def test_retrieval_from_query_file():
    """Test retrieval using query request from file."""
    
    print("\n" + "=" * 80)
    print("TEST: Retrieval Pipeline from Query File")
    print("=" * 80)
    
    # Load query request
    query_file = project_root / "sample_queries" / "query_request.json"
    
    if not query_file.exists():
        print(f"[ERROR] Query file not found: {query_file}")
        print("Please create sample_queries/query_request.json")
        return
    
    with open(query_file, 'r') as f:
        query_request = json.load(f)
    
    print(f"[Test] Loaded query: {query_file.name}")
    print(f"[Test] Tokens: {len(query_request.get('tokens', []))}")
    print(f"[Test] Top-K: {query_request.get('top_k')}")
    
    # Initialize pipeline
    pipeline = RetrievalPipeline(
        similarity_service_url="http://localhost:8000/api/v1/search",
        output_dir="retrieved_images"
    )
    
    # Execute retrieval
    try:
        saved_files = pipeline.retrieve_and_decrypt(
            query_request=query_request,
            query_id="test_query_001"
        )
        
        # Verify results
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print(f"Images saved: {len(saved_files)}")
        
        if saved_files:
            print("\nSaved files:")
            for file_info in saved_files:
                print(f"  Rank {file_info['rank']}: {file_info['file_path']}")
            print("\n✅ TEST PASSED")
        else:
            print("\n⚠️  TEST COMPLETED: No images retrieved")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_retrieval_from_json_response():
    """Test retrieval from pre-fetched JSON response."""
    
    print("\n" + "=" * 80)
    print("TEST: Retrieval from JSON Response")
    print("=" * 80)
    
    # Load search results from file
    results_file = project_root / "sample_queries" / "search_response.json"
    
    if not results_file.exists():
        print(f"[SKIP] Response file not found: {results_file}")
        print("Run test_retrieval_from_query_file() first to generate results")
        return
    
    with open(results_file, 'r') as f:
        search_response = json.load(f)
    
    results = search_response.get('results', [])
    
    print(f"[Test] Loaded {len(results)} search results")
    
    # Initialize pipeline
    pipeline = RetrievalPipeline(output_dir="retrieved_images")
    
    # Execute retrieval (skip HTTP query)
    try:
        saved_files = pipeline.retrieve_from_results(
            search_results=results,
            query_id="test_query_002"
        )
        
        # Verify results
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print(f"Images saved: {len(saved_files)}")
        
        if saved_files:
            print("✅ TEST PASSED")
        else:
            print("⚠️  TEST COMPLETED: No images retrieved")
            
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 80)
    print("RETRIEVAL PIPELINE TEST SUITE")
    print("=" * 80)
    
    # Test 1: Full pipeline with HTTP query
    test_retrieval_from_query_file()
    
    # Test 2: Pipeline with pre-fetched results
    # test_retrieval_from_json_response()
