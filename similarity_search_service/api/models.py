from pydantic import BaseModel, Field
from typing import List, Dict, Any

class SearchRequest(BaseModel):
    """Similarity search request model."""
    
    tokens: List[str] = Field(
        ..., 
        description="LSH tokens for candidate retrieval",
        min_items=1
    )
    query_fhe_ct: str = Field(
        ..., 
        description="Base64-encoded BFV encrypted hash"
    )
    top_k: int = Field(
        default=10, 
        ge=1, 
        le=100,
        description="Number of top results to return"
    )
    tenant_id: str = Field(
        ...,
        description="Tenant ID for multi-tenancy"
    )

class CandidateResult(BaseModel):
    """Single candidate result."""
    
    blob_name: str = Field(..., description="Azure Blob Storage blob name")
    rank: int = Field(..., description="Rank in top-K results (1-indexed, 1=most similar)")
    encrypted_distance: str = Field(
        ..., 
        description="Base64-encoded encrypted Hamming distance"
    )
    metadata: Dict[str, Any] = Field(
        ...,
        description="Full JSON object from blob storage"
    )

class SearchResponse(BaseModel):
    """Similarity search response model."""
    
    status: str = Field(default="success")
    num_candidates: int = Field(..., description="Total candidates evaluated")
    results: List[CandidateResult] = Field(
        ..., 
        description="Top-K results ordered by rank (1=most similar)"
    )
    processing_time_ms: float = Field(
        ..., 
        description="Total server-side processing time"
    )
    ranking_time_ms: float = Field(
        default=0.0,
        description="Time spent on FHE ranking"
    )
