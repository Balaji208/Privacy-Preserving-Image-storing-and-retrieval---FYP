# crypto/csprng.py

import os

class CSPRNG:
    """
    Cryptographically Secure Random Number Generator
    Uses OS entropy source (ChaCha20-DRBG internally)
    """

    @staticmethod
    def generate_cek() -> bytes:
        """
        Generate a 256-bit Content Encryption Key (CEK)
        Returns:
            CEK (32 bytes)
        """
        return os.urandom(32)

    @staticmethod
    def generate_nonce() -> bytes:
        """
        Generate a 96-bit nonce for AES-GCM
        Returns:
            nonce (12 bytes)
        """
        return os.urandom(12)

    @staticmethod
    def generate_salt(length: int = 32) -> bytes:
        """
        Generate random salt for HKDF
        Args:
            length: salt length in bytes (default 32)
        Returns:
            salt bytes
        """
        if length < 16:
            raise ValueError("Salt length must be at least 16 bytes")
        return os.urandom(length)

