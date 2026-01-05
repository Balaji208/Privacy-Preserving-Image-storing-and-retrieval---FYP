"""
BFV-Based Fully Homomorphic Encryption Module
==============================================
Production-ready BFV encryption for binary hash vectors.

Features:
    - 128-bit+ post-quantum security (RLWE-based)
    - Encrypted Hamming distance computation
    - SoftHSM integration for key management
    - Thread-safe operations
    - Serialization for storage/transmission

Main API:
    >>> from fhe_bfv import BFVPipeline
    >>> import numpy as np
    >>> 
    >>> pipeline = BFVPipeline()
    >>> hash_256 = np.random.randint(0, 2, 256)
    >>> ctxt = pipeline.encrypt(hash_256)

Author: Applied Cryptography Research Team
Version: 1.0.0
License: MIT
"""

from .pipeline.fhe_pipeline import BFVPipeline
from .config.bfv_params import BFVParams
from .context.bfv_context import BFVContext
from .keys.key_loader import BFVKeyLoader

__version__ = "1.0.0"
__all__ = [
    "BFVPipeline",
    "BFVParams",
    "BFVContext",
    "BFVKeyLoader",
]
