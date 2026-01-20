"""
Serialization Utilities
========================

Handles encoding/decoding of FHE ciphertexts and binary data.
"""

import logging
import base64
import tenseal as ts
from typing import Union

from fhe.context_loader import FHEContextLoader

logger = logging.getLogger(__name__)


def deserialize_fhe_vector(
    base64_ciphertext: str,
    context_loader: FHEContextLoader
) -> ts.BFVVector:
    """
    Deserialize base64-encoded FHE ciphertext to TenSEAL BFVVector.
    
    Args:
        base64_ciphertext: Base64-encoded BFV ciphertext
        context_loader: FHE context loader
    
    Returns:
        TenSEAL BFVVector
    
    Raises:
        ValueError: If deserialization fails
    """
    try:
        # Decode base64
        ciphertext_bytes = base64.b64decode(base64_ciphertext)
        
        # Deserialize to BFVVector
        context = context_loader.get_context()
        fhe_vector = ts.bfv_vector_from(context, ciphertext_bytes)
        
        logger.debug(f"✓ Deserialized FHE vector: {len(ciphertext_bytes)} bytes")
        return fhe_vector
        
    except Exception as e:
        logger.error(f"✗ FHE deserialization failed: {e}")
        raise ValueError(f"Invalid FHE ciphertext: {e}")


def serialize_fhe_vector(fhe_vector: ts.BFVVector) -> str:
    """
    Serialize TenSEAL BFVVector to base64 string.
    
    Args:
        fhe_vector: TenSEAL BFVVector
    
    Returns:
        Base64-encoded ciphertext string
    """
    try:
        ciphertext_bytes = fhe_vector.serialize()
        base64_ct = base64.b64encode(ciphertext_bytes).decode('utf-8')
        return base64_ct
    except Exception as e:
        logger.error(f"✗ FHE serialization failed: {e}")
        raise
