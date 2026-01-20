"""Pipeline module."""

# Try TenSEAL first (recommended)
try:
    from .tenseal_hsm_pipeline import BFVPipeline
    __all__ = ["BFVPipeline"]
except ImportError:
    # Try Pyfhel (requires compilation)
    try:
        from .fhe_pipeline import BFVPipeline as PyfhelBFVPipeline
        BFVPipeline = PyfhelBFVPipeline
        __all__ = ["BFVPipeline"]
    except ImportError:
        # No FHE available
        BFVPipeline = None
        __all__ = []
