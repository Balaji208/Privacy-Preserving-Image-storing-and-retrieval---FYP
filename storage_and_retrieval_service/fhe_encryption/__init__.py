"""
BFV-Based Fully Homomorphic Encryption Module
==============================================

Production-ready BFV encryption using TenSEAL + SoftHSM.

Quick Start:
    from fhe_encryption import BFVPipeline
    import numpy as np
    
    # Client-side (encryption only)
    pipeline = BFVPipeline(load_secret_key=False)
    deephash = np.random.randint(0, 2, 256)  # From DeepHash
    ciphertext = pipeline.encrypt(deephash)
    
    # Server-side (with decryption)
    server_pipeline = BFVPipeline(load_secret_key=True)
    decrypted = server_pipeline.decrypt(ciphertext)

Backend: TenSEAL (Microsoft SEAL)
Version: 2.0.0
"""

__version__ = "2.0.0"

FHE_AVAILABLE = False
BFVPipeline = None

# Load TenSEAL pipeline
try:
    from .pipeline.tenseal_hsm_pipeline import BFVPipeline
    FHE_AVAILABLE = True
    print("✓ FHE loaded: TenSEAL + SoftHSM")
except ImportError as e:
    print(f"✗ FHE not available: {e}")
    print(f"   Install: pip install tenseal")
    BFVPipeline = None

__all__ = ['BFVPipeline', 'FHE_AVAILABLE']
