import tenseal as ts
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

class BFVContextLoader:
    """Load and manage BFV context for FHE operations."""
    
    _instance = None
    _context = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_context(self, context_path: str) -> ts.Context:
        """Load BFV context from file (singleton pattern)."""
        
        if self._context is not None:
            logger.debug("Using cached BFV context")
            return self._context
        
        path = Path(context_path)
        
        if not path.exists():
            raise FileNotFoundError(f"BFV context not found: {context_path}")
        
        logger.info(f"Loading BFV context from {context_path}")
        
        with open(path, 'rb') as f:
            context_bytes = f.read()
        
        self._context = ts.context_from(context_bytes)
        
        # Log context info (use correct TenSEAL attribute names)
        try:
            logger.info(
                f"BFV context loaded successfully - "
                f"Is public: {self._context.is_public()}"
            )
            
            # Try to get additional info if available
            if hasattr(self._context, 'global_scale'):
                logger.info(f"Global scale: {self._context.global_scale}")
            
        except Exception as e:
            logger.warning(f"Could not retrieve full context info: {e}")
            logger.info("BFV context loaded successfully")
        
        if not self._context.is_public():
            logger.warning("⚠️  Context contains secret key - should be public only!")
        else:
            logger.info("✅ Context is public-only (no secret key)")
        
        return self._context
    
    def get_context(self) -> ts.Context:
        """Get loaded context (must call load_context first)."""
        
        if self._context is None:
            raise RuntimeError("Context not loaded. Call load_context() first.")
        
        return self._context
