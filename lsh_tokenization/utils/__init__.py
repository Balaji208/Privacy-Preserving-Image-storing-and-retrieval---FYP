"""Utility modules."""

from .bit_utils import BitUtils
from .security import SecurityUtils

# HSM integration (optional)
try:
    from .hsm_key_manager import (
        HSMKeyManager,
        initialize_hmac_key_in_hsm,
        load_hmac_key_from_hsm
    )
    __all__ = [
        "BitUtils",
        "SecurityUtils",
        "HSMKeyManager",
        "initialize_hmac_key_in_hsm",
        "load_hmac_key_from_hsm"
    ]
except ImportError:
    __all__ = ["BitUtils", "SecurityUtils"]
