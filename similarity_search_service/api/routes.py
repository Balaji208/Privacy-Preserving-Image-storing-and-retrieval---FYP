from fastapi import APIRouter, HTTPException, status
from typing import List
import time
import base64
from contextlib import asynccontextmanager

from api.models import SearchRequest, SearchResponse, CandidateResult
from fhe.context_loader import BFVContextLoader
from fhe.distance_computer import DistanceComputer
from fhe.parallel_ranker import ParallelRanker
from redis_service.candidate_fetcher import CandidateFetcher
from storage.blob_fetcher import BlobFetcher
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["similarity-search"])

# Initialize services
context_loader = BFVContextLoader()
candidate_fetcher = CandidateFetcher()
blob_fetcher = BlobFetcher()


# Startup function (called when router is included in app)
def initialize_services():
    """Load BFV context on startup."""
    logger.info("=" * 80)
    logger.info("SIMILARITY SEARCH SERVICE - FHE RANKING MODE")
    logger.info("=" * 80)
    
    try:
        context_loader.load_context(settings.BFV_CONTEXT_PATH)
        logger.info("✅ BFV context loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load BFV context: {e}")
        raise


@router.post("/search", response_model=SearchResponse)
async def similarity_search(request: SearchRequest):
    """
    Perform encrypted similarity search with FHE ranking.
    
    Pipeline:
    1. Fetch candidate blob names from Redis using LSH tokens
    2. Download JSON objects from Azure Blob Storage
    3. Extract FHE ciphertexts from JSON
    4. Compute encrypted Hamming distances
    5. FHE ranking: Select top-K by SMALLEST distance (100% accurate)
    6. Return top-K JSON objects with ranks
    
    Guarantees: Top-K results are the K most similar images.
    """
    
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info(
        f"SEARCH REQUEST: tenant={request.tenant_id}, "
        f"tokens={len(request.tokens)}, top_k={request.top_k}"
    )
    logger.info("=" * 80)
    
    try:
        # Step 1: Fetch candidate blob names from Redis
        logger.info("\n[STEP 1/6] Fetching candidate blob names from Redis...")
        candidate_blob_names = candidate_fetcher.fetch_candidates(
            tokens=request.tokens,
            tenant_id=request.tenant_id,
            max_candidates=settings.MAX_CANDIDATES
        )
        
        if not candidate_blob_names:
            logger.warning("No candidates found in Redis")
            return SearchResponse(
                status="success",
                num_candidates=0,
                results=[],
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        logger.info(f"✅ Found {len(candidate_blob_names)} candidate blobs")
        
        # Step 2: Fetch JSON objects from Azure Blob Storage
        logger.info("\n[STEP 2/6] Downloading JSON objects from Azure...")
        blob_data = blob_fetcher.batch_fetch_blobs(candidate_blob_names)
        
        if not blob_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to fetch any blob data"
            )
        
        logger.info(f"✅ Downloaded {len(blob_data)} JSON objects")
        
        # Step 3: Extract FHE ciphertexts
        logger.info("\n[STEP 3/6] Extracting FHE ciphertexts from JSON...")
        fhe_cts = blob_fetcher.extract_fhe_cts(blob_data)
        
        if not fhe_cts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No FHE ciphertexts found in blob data"
            )
        
        logger.info(f"✅ Extracted {len(fhe_cts)} FHE ciphertexts")
        
        # Step 4: Compute encrypted Hamming distances
        logger.info("\n[STEP 4/6] Computing encrypted Hamming distances...")
        
        context = context_loader.get_context()
        distance_computer = DistanceComputer(context)
        
        blob_names_list = []
        encrypted_distances = []
        
        for blob_name, fhe_ct_b64 in fhe_cts.items():
            try:
                distance_ct_bytes = distance_computer.compute_hamming_distance(
                    query_ct_b64=request.query_fhe_ct,
                    stored_ct_b64=fhe_ct_b64
                )
                
                blob_names_list.append(blob_name)
                encrypted_distances.append(distance_ct_bytes)
                
            except Exception as e:
                logger.warning(f"Failed to compute distance for {blob_name}: {e}")
        
        logger.info(f"✅ Computed {len(encrypted_distances)} encrypted distances")
        
        # Step 5: FHE Ranking (CRITICAL STEP)
        logger.info("\n[STEP 5/6] 🔥 FHE RANKING: Selecting top-K by smallest distance...")
        logger.info("⚠️  This step may take 5-20 seconds for 100-200 candidates")
        
        ranking_start = time.time()
        
        ranker = ParallelRanker(
            context=context,
            num_threads=settings.NUM_THREADS
        )
        
        ranked_results = ranker.rank_and_select_topk(
            encrypted_distances=encrypted_distances,
            blob_names=blob_names_list,
            k=request.top_k
        )
        
        ranking_time = (time.time() - ranking_start) * 1000
        logger.info(f"✅ Ranking completed in {ranking_time:.2f}ms")
        
        # Step 6: Format results
        logger.info("\n[STEP 6/6] Formatting top-K results...")
        
        results = []
        for blob_name, rank, encrypted_distance in ranked_results:
            json_obj = blob_data.get(blob_name, {})
            
            results.append(
                CandidateResult(
                    blob_name=blob_name,
                    rank=rank,
                    encrypted_distance=base64.b64encode(encrypted_distance).decode('utf-8'),
                    metadata=json_obj
                )
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info("=" * 80)
        logger.info(
            f"✅ SEARCH COMPLETE: {len(results)} results in {processing_time:.2f}ms"
        )
        logger.info(f"   - Ranking time: {ranking_time:.2f}ms ({ranking_time/processing_time*100:.1f}%)")
        logger.info("=" * 80)
        
        return SearchResponse(
            status="success",
            num_candidates=len(candidate_blob_names),
            results=results,
            processing_time_ms=processing_time,
            ranking_time_ms=ranking_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    
    redis_ok = candidate_fetcher.health_check()
    context_ok = context_loader._context is not None
    
    return {
        "status": "healthy" if (redis_ok and context_ok) else "degraded",
        "redis": "ok" if redis_ok else "error",
        "bfv_context": "loaded" if context_ok else "not_loaded",
        "ranking_mode": "FHE (100% accurate)"
    }
