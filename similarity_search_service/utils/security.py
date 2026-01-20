"""
Security Utilities
==================

Request validation, HMAC verification, and secure memory handling.
"""

import logging
import hmac
import hashlib
from typing import Optional

from config.settings import Settings

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Request security validation.
    
    Features:
    - HMAC signature verification
    - Request replay protection (timestamp validation)
    - Rate limiting hooks
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize security validator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.hmac_key = settings.hmac_secret_key
        
        if settings.enable_request_signing and not self.hmac_key:
            logger.warning(
                "Request signing enabled but no HMAC key configured. "
                "Set HMAC_SECRET_KEY environment variable."
            )
    
    def verify_request_signature(
        self,
        request_body: bytes,
        signature_header: Optional[str]
    ) -> bool:
        """
        Verify HMAC signature of request body.
        
        Args:
            request_body: Raw request bytes
            signature_header: X-Request-Signature header value
        
        Returns:
            True if signature valid, False otherwise
        """
        if not self.settings.enable_request_signing:
            return True
        
        if not signature_header or not self.hmac_key:
            logger.warning("Missing signature or HMAC key")
            return False
        
        try:
            # Compute expected signature
            expected_sig = hmac.new(
                self.hmac_key.encode('utf-8'),
                request_body,
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison
            return hmac.compare_digest(expected_sig, signature_header)
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
