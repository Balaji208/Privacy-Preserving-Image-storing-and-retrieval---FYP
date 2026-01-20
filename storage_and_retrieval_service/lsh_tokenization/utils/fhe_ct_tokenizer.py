"""
FHE Ciphertext HMAC Tokenizer
==============================

Generates HMAC tokens from FHE ciphertexts for Azure Table storage key generation.
"""

import hashlib
import hmac
from typing import Union
import logging

logger = logging.getLogger(__name__)

class FHECTTokenizer:
    """
    Generate HMAC tokens for FHE ciphertexts.
    
    This creates deterministic tokens: HMAC(FHE_CT || image_id)
    These tokens match Azure Table storage keys for efficient lookups.
    
    Design:
    - Uses same HMAC key as LSH tokenization (from HSM)
    - image_id acts as salt for uniqueness
    - Deterministic: same (FHE_CT, image_id) → same token
    """
    
    def __init__(self, hmac_key: bytes):
        """
        Initialize FHE CT tokenizer.
        
        Args:
            hmac_key: 32-byte HMAC key from HSM
        """
        if len(hmac_key) != 32:
            raise ValueError(f"HMAC key must be 32 bytes, got {len(hmac_key)}")
        
        self._hmac_key = hmac_key
        logger.info("Initialized FHE CT tokenizer")
    
    def tokenize_fhe_ct(
        self,
        fhe_ct: bytes,
        image_id: str
    ) -> str:
        """
        Generate HMAC token for FHE ciphertext.
        
        Args:
            fhe_ct: FHE ciphertext bytes (~88 KB)
            image_id: Image identifier (used as salt)
        
        Returns:
            Hex-encoded HMAC token (64 characters)
        
        Formula:
            token = HMAC-SHA3-256(hmac_key, fhe_ct || image_id)
        
        Example:
            >>> tokenizer = FHECTTokenizer(hmac_key)
            >>> token = tokenizer.tokenize_fhe_ct(fhe_ct_bytes, "IMG_001")
            >>> len(token)
            64  # 32 bytes in hex
        """
        # Construct message: fhe_ct || image_id
        image_id_bytes = image_id.encode('utf-8')
        message = fhe_ct + image_id_bytes
        
        # Compute HMAC-SHA3-256
        h = hmac.new(
            self._hmac_key,
            message,
            hashlib.sha3_256
        )
        
        token = h.hexdigest()
        
        logger.debug(
            f"Generated FHE CT token for image_id={image_id}: "
            f"{token[:16]}... (FHE CT size: {len(fhe_ct):,} bytes)"
        )
        
        return token
    
    def tokenize_batch(
        self,
        fhe_cts: list[bytes],
        image_ids: list[str]
    ) -> list[str]:
        """
        Batch tokenize multiple FHE ciphertexts.
        
        Args:
            fhe_cts: List of FHE ciphertext bytes
            image_ids: List of corresponding image IDs
        
        Returns:
            List of HMAC tokens
        
        Raises:
            ValueError: If lists have different lengths
        """
        if len(fhe_cts) != len(image_ids):
            raise ValueError(
                f"fhe_cts and image_ids must have same length: "
                f"{len(fhe_cts)} != {len(image_ids)}"
            )
        
        tokens = [
            self.tokenize_fhe_ct(fhe_ct, image_id)
            for fhe_ct, image_id in zip(fhe_cts, image_ids)
        ]
        
        logger.debug(f"Generated {len(tokens)} FHE CT tokens")
        return tokens


def load_hmac_key_for_fhe_tokenizer() -> bytes:
    """
    Load HMAC key from HSM for FHE CT tokenization.
    
    Uses the same key as LSH bucket tokenization (LSH_HMAC_KEY).
    
    Returns:
        32-byte HMAC key
    
    Raises:
        RuntimeError: If HSM not available or key not found
    """
    try:
        from .hsm_key_manager import load_hmac_key_from_hsm
        return load_hmac_key_from_hsm("LSH_HMAC_KEY")
    except ImportError:
        raise RuntimeError(
            "HSM modules not available. Install python-pkcs11."
        )
    except ValueError:
        # Key not found
        raise RuntimeError(
            "LSH_HMAC_KEY not found in HSM. Run LSH initialization first."
        )
