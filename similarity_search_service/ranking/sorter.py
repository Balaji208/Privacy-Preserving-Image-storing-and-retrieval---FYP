"""
Ranking and Sorting Module
===========================

Sorts candidates by decrypted Hamming distance and selects top-K.
"""

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class CandidateSorter:
    """
    Sorts candidates by Hamming distance and selects top-K results.
    
    Input: List of (candidate_index, hamming_distance) tuples
    Output: Top-K candidates sorted by distance (ascending)
    """
    
    def __init__(self):
        """Initialize sorter."""
        logger.info("Candidate sorter initialized")
    
    def sort_and_select_topk(
        self,
        candidates_with_distances: List[Tuple[int, Optional[int]]],
        top_k: int
    ) -> List[Tuple[int, int]]:
        """
        Sort candidates by Hamming distance and return top-K.
        
        Args:
            candidates_with_distances: List of (index, distance) tuples
            top_k: Number of top results to return
        
        Returns:
            List of (index, distance) for top-K candidates
            Sorted by distance (ascending): lower distance = more similar
        
        Note:
            - Filters out None distances (decryption failures)
            - Returns fewer than top_k if insufficient valid candidates
        """
        # Filter out failed decryptions
        valid_candidates = [
            (idx, dist)
            for idx, dist in candidates_with_distances
            if dist is not None
        ]
        
        if not valid_candidates:
            logger.warning("No valid candidates to sort")
            return []
        
        # Sort by Hamming distance (ascending)
        sorted_candidates = sorted(
            valid_candidates,
            key=lambda x: x[1]  # Sort by distance
        )
        
        # Select top-K
        topk_candidates = sorted_candidates[:top_k]
        
        logger.info(
            f"✓ Sorted {len(valid_candidates)} candidates, "
            f"selected top-{len(topk_candidates)}"
        )
        
        return topk_candidates
    
    def get_ranking_stats(
        self,
        candidates_with_distances: List[Tuple[int, Optional[int]]]
    ) -> dict:
        """
        Compute ranking statistics.
        
        Returns:
            Dictionary with min/max/mean distances, etc.
        """
        valid_distances = [
            dist
            for _, dist in candidates_with_distances
            if dist is not None
        ]
        
        if not valid_distances:
            return {
                "count": 0,
                "min_distance": None,
                "max_distance": None,
                "mean_distance": None
            }
        
        return {
            "count": len(valid_distances),
            "min_distance": min(valid_distances),
            "max_distance": max(valid_distances),
            "mean_distance": sum(valid_distances) / len(valid_distances)
        }
