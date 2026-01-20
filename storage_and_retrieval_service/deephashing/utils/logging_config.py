"""Logging configuration"""

import logging


def setup_logging(level: str = 'INFO'):
    """Setup logging for the package"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(levelname)s: %(message)s'
    )
