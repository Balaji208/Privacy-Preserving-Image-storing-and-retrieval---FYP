"""
Image Encryption Processor
===========================
Handles image encryption using Kyber + AES-GCM
"""

import logging
from typing import Dict
from datetime import datetime
from image_encryption.image_encryptor import ImageEncryptor
from image_encryption.utils.image_io import read_image_bytes

logger = logging.getLogger(__name__)

class EncryptionProcessor:
    """Handles image encryption."""
    
    def __init__(self):
        """Initialize image encryptor."""
        self.encryptor = ImageEncryptor()
        logger.info("✓ Encryption processor initialized")
    
    def encrypt(
        self,
        image_path: str,
        image_id: str,
        user_id: str = "default_user"
    ) -> Dict:
        """
        Encrypt image.
        
        Args:
            image_path: Path to image file
            image_id: Unique image identifier
            user_id: User identifier
            
        Returns:
            Encrypted image JSON
        """
        image_bytes = read_image_bytes(image_path)
        timestamp = datetime.now().isoformat()
        
        encrypted_json = self.encryptor.encrypt_image(
            image_bytes=image_bytes,
            image_id=image_id,
            user_id=user_id,
            timestamp=timestamp
        )
        
        logger.debug(f"✓ Image encrypted: {len(str(encrypted_json))} bytes")
        return encrypted_json
