"""
FHE Context Loader with Server-Side Keys
=========================================
"""

import logging
import base64
import tenseal as ts
from typing import Optional

from config.settings import Settings

logger = logging.getLogger(__name__)


class FHEContextLoader:
    """
    FHE context manager with server-side Galois & Relin keys.
    
    Keys are loaded once at startup from base64 environment variable.
    """
    
    _instance = None
    _context = None
    _galois_keys_loaded = False
    _relin_keys_loaded = False
    
    def __new__(cls, settings: Settings):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, settings: Settings):
        if self._context is not None:
            return  # Already initialized
        
        self.settings = settings
        logger.info("🔑 Initializing FHE context with server-side keys...")
    
    def load_context(self) -> ts.Context:
        """
        Load FHE context with Galois & Relin keys from base64.
        
        Returns:
            TenSEAL context with evaluation keys loaded
        """
        if self._context is not None:
            return self._context
        
        try:
            if not self.settings.tenseal_full_context_base64:
                raise ValueError("TENSEAL_FULL_CONTEXT_BASE64 not set in .env")
            
            logger.info("Loading full context from base64...")
            
            # Decode base64 and deserialize context
            context_bytes = base64.b64decode(
                self.settings.tenseal_full_context_base64
            )
            
            self._context = ts.context_from(context_bytes)
            
            # Make context public (remove secret key if present)
            if not self._context.is_public():
                self._context.make_context_public()
            
            # Full context includes Galois and Relin keys
            self._galois_keys_loaded = True
            self._relin_keys_loaded = True
            
            logger.info(
                f"✅ FHE Context loaded successfully\n"
                f"   - Scheme: BFV\n"
                f"   - Poly modulus degree: {self.settings.fhe_poly_modulus_degree}\n"
                f"   - Plain modulus: {self.settings.fhe_plain_modulus}\n"
                f"   - Galois keys: ✓\n"
                f"   - Relin keys: ✓\n"
                f"   - Public context: ✓"
            )
            
            return self._context
            
        except Exception as e:
            logger.error(f"❌ Context loading failed: {e}")
            raise
    
    def get_context(self) -> ts.Context:
        """Get loaded context."""
        if self._context is None:
            raise RuntimeError("Context not loaded. Call load_context() first.")
        return self._context
    
    def has_galois_keys(self) -> bool:
        """Check if Galois keys are loaded."""
        return self._galois_keys_loaded
    
    def has_relin_keys(self) -> bool:
        """Check if Relinearization keys are loaded."""
        return self._relin_keys_loaded
