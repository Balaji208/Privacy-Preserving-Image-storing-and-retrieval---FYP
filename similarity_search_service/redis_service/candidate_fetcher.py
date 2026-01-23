import redis
from typing import List, Set
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class CandidateFetcher:
    """Fetch candidate blob names from Redis using LSH tokens."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        logger.info(f"Redis client initialized: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    
    def fetch_candidates(
        self,
        tokens: List[str],
        tenant_id: str = None,  # Ignored for now
        max_candidates: int = 150
    ) -> List[str]:
        """
        Fetch candidate blob names from Redis using LSH tokens.
        
        Redis key format: lsh:token:{token_hash}
        Redis value type: LIST (not SET)
        
        Args:
            tokens: List of LSH token hashes
            tenant_id: Ignored (for future use)
            max_candidates: Maximum number of candidates to return
        
        Returns:
            List of unique blob names (without .json extension)
        """
        
        logger.info(
            f"Fetching candidates for {len(tokens)} tokens (max={max_candidates})"
        )
        
        all_candidates = set()
        
        for token in tokens:
            # Use the correct Redis key format: lsh:token:{hash}
            key = f"lsh:token:{token}"
            
            try:
                # Fetch blob names from Redis LIST (not SET!)
                # LRANGE key 0 -1 gets all elements
                blob_names = self.redis_client.lrange(key, 0, -1)
                
                if blob_names:
                    all_candidates.update(blob_names)
                    logger.info(f"Token '{token[:16]}...': {len(blob_names)} candidates")
                else:
                    logger.debug(f"Token '{token[:16]}...': No candidates found")
                    
            except Exception as e:
                logger.error(f"Error fetching candidates for token {token[:16]}...: {e}")
        
        # Convert to list and limit
        candidates = list(all_candidates)[:max_candidates]
        
        logger.info(
            f"Found {len(all_candidates)} unique candidates "
            f"(returning {len(candidates)})"
        )
        
        return candidates
    
    def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
