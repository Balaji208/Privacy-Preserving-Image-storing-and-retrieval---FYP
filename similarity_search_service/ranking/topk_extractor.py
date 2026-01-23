from typing import List, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)

class TopKExtractor:
    """Extract top-K results from ranked candidates."""
    
    @staticmethod
    def extract_topk(
        ranked_results: List[Tuple[str, int, bytes]],
        k: int
    ) -> List[Tuple[str, int, bytes]]:
        """
        Extract top-K results from ranked list.
        
        Args:
            ranked_results: List of (blob_name, rank, encrypted_distance)
            k: Number of top results
        
        Returns:
            Top-K results sorted by rank
        """
        
        # Sort by rank (second element)
        sorted_results = sorted(ranked_results, key=lambda x: x[1])
        
        # Return top K
        topk = sorted_results[:k]
        
        logger.info(f"Extracted top-{k} from {len(ranked_results)} candidates")
        
        return topk
    
    @staticmethod
    def format_results(
        topk_results: List[Tuple[str, int, bytes]]
    ) -> List[dict]:
        """
        Format results for API response.
        
        Args:
            topk_results: List of (blob_name, rank, encrypted_distance)
        
        Returns:
            List of formatted result dictionaries
        """
        
        import base64
        
        formatted = []
        
        for blob_name, rank, encrypted_distance in topk_results:
            formatted.append({
                'blob_name': blob_name,
                'rank': rank,
                'encrypted_distance': base64.b64encode(encrypted_distance).decode('utf-8')
            })
        
        return formatted
