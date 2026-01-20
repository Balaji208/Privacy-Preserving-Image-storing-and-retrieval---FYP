"""
API Models
==========

Pydantic models for request/response validation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Single-round search request with evaluation keys.
    
    Client sends:
    - Encrypted query hash
    - LSH tokens
    - Galois keys (safe to expose)
    - Relinearization keys (safe to expose)
    """
    
    tokens: List[str] = Field(
        ...,
        min_items=1,
        max_items=20,
        description="LSH tokens for candidate collection"
    )
    
    query_fhe_hash: str = Field(
        ...,
        description="Base64 BFV encrypted query hash"
    )
    
    galois_keys: str = Field(
        ...,
        description="Base64 serialized Galois keys (public evaluation keys)"
    )
    
    relin_keys: Optional[str] = Field(
        default=None,
        description="Base64 serialized relinearization keys (optional)"
    )
    
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top results to return"
    )
    
    decryption_service_url: str = Field(
        ...,
        description="URL of client's decryption service (for HSM access)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "tokens": ["a1b2c3d4e5f67890", "f0e1d2c3b4a59687"],
                "query_fhe_hash": "SGVsbG8gV29ybGQh...",
                "galois_keys": "R2Fsb2lzS2V5cw==...",
                "relin_keys": "UmVsaW5LZXlz...",
                "top_k": 5,
                "decryption_service_url": "http://localhost:9000/decrypt"
            }
        }


class ImageResult(BaseModel):
    """Single image result with distance."""
    
    image_id: str = Field(..., description="Unique image identifier")
    
    hamming_distance: int = Field(
        ...,
        ge=0,
        le=256,
        description="Hamming distance from query (0=identical, 256=opposite)"
    )
    
    encrypted_image: str = Field(
        ...,
        description="Base64 encrypted image data"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Image metadata"
    )
    
    rank: int = Field(
        ...,
        ge=1,
        description="Rank in Top-K results (1=most similar)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_id": "img_12345",
                "hamming_distance": 23,
                "encrypted_image": "aGVsbG8gd29ybGQ=...",
                "metadata": {
                    "filename": "sample.jpg",
                    "upload_date": "2026-01-19"
                },
                "rank": 1
            }
        }


class SearchResponse(BaseModel):
    """Search response with Top-K results."""
    
    results: List[ImageResult] = Field(
        default_factory=list,
        description="Top-K images sorted by similarity (rank 1 = most similar)"
    )
    
    query_time_ms: float = Field(
        ...,
        description="Total query processing time in milliseconds"
    )
    
    candidates_evaluated: int = Field(
        ...,
        description="Number of candidates evaluated"
    )
    
    fhe_operations_count: int = Field(
        ...,
        description="Number of FHE operations performed"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "image_id": "img_12345",
                        "hamming_distance": 23,
                        "encrypted_image": "aGVsbG8=...",
                        "metadata": {"filename": "sample1.jpg"},
                        "rank": 1
                    }
                ],
                "query_time_ms": 1234.56,
                "candidates_evaluated": 150,
                "fhe_operations_count": 300
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service health status")
    redis_connected: bool = Field(..., description="Redis connection status")
    azure_connected: bool = Field(..., description="Azure Storage connection status")
    fhe_context_loaded: bool = Field(..., description="FHE context loaded status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "redis_connected": True,
                "azure_connected": True,
                "fhe_context_loaded": True
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request parameters",
                "detail": "tokens must contain at least 1 item"
            }
        }


# Additional models for future endpoints

class BatchSearchRequest(BaseModel):
    """Batch search request for multiple queries."""
    
    queries: List[SearchRequest] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of search requests (max 10)"
    )


class BatchSearchResponse(BaseModel):
    """Batch search response."""
    
    results: List[SearchResponse] = Field(
        ...,
        description="Results for each query"
    )
    
    total_time_ms: float = Field(
        ...,
        description="Total processing time for all queries"
    )


class StatsResponse(BaseModel):
    """Service statistics response."""
    
    total_searches: int = Field(..., description="Total searches performed")
    avg_query_time_ms: float = Field(..., description="Average query time")
    total_candidates_evaluated: int = Field(..., description="Total candidates evaluated")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
