"""
Secure Memory Zeroization
==========================
Best-effort memory clearing for sensitive data.

Security Note:
    Python's garbage collector and memory management make true
    memory zeroization difficult. This provides best-effort clearing.
"""

import logging

logger = logging.getLogger(__name__)


def secure_zero_bytes(data: bytearray) -> None:
    """
    Zero out byte array in memory.
    
    Args:
        data: Bytearray to zero
        
    Note:
        This is best-effort. Python may have created copies
        that remain in memory after GC.
    """
    if not isinstance(data, bytearray):
        logger.warning(
            f"secure_zero_bytes expects bytearray, got {type(data)}"
        )
        return
    
    # Overwrite with zeros
    for i in range(len(data)):
        data[i] = 0
    
    logger.debug(f"Zeroized {len(data)} bytes")


def secure_zero_list(data: list) -> None:
    """
    Zero out list of numeric values.
    
    Args:
        data: List to zero
    """
    for i in range(len(data)):
        data[i] = 0
    
    logger.debug(f"Zeroized list of {len(data)} elements")


def secure_del(obj) -> None:
    """
    Delete object and attempt to clear from memory.
    
    Args:
        obj: Object to delete
    """
    try:
        if isinstance(obj, bytearray):
            secure_zero_bytes(obj)
        elif isinstance(obj, list):
            secure_zero_list(obj)
    except Exception as e:
        logger.warning(f"Failed to zero object: {e}")
    finally:
        del obj
