# crypto/cek_wrap.py

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from image_encryption.crypto.csprng import CSPRNG 


class CEKWrapper:
    """
    CEK Wrapping Module (Envelope Encryption Layer)

    Encrypts (wraps) the Content Encryption Key (CEK)
    using a derived Key Encryption Key (KEK) via AES-256-GCM
    """

    @staticmethod
    def wrap_cek(cek: bytes, kek: bytes, aad: bytes = b"CEK-WRAPPING") -> dict:
        """
        Wrap (encrypt) CEK using AES-256-GCM

        Args:
            cek : Content Encryption Key (32 bytes)
            kek : Key Encryption Key (32 bytes)
            aad : Optional associated data

        Returns:
            {
                "wrapped_cek": bytes,
                "nonce": bytes,
                "tag": bytes
            }
        """

        if len(cek) != 32:
            raise ValueError("CEK must be 32 bytes (256-bit AES key)")

        if len(kek) != 32:
            raise ValueError("KEK must be 32 bytes (256-bit AES key)")

        # AES-GCM requires a 96-bit nonce
        nonce = CSPRNG.generate_nonce()

        aesgcm = AESGCM(kek)

        # Encrypt CEK
        ciphertext = aesgcm.encrypt(nonce, cek, aad)

        # Split ciphertext and authentication tag
        wrapped_cek = ciphertext[:-16]
        tag = ciphertext[-16:]

        return {
            "wrapped_cek": wrapped_cek,
            "nonce": nonce,
            "tag": tag
        }

    @staticmethod
    def unwrap_cek(wrapped_cek: bytes, nonce: bytes, tag: bytes, kek: bytes, aad: bytes = b"CEK-WRAPPING") -> bytes:
        """
        Unwrap (decrypt) CEK using AES-256-GCM

        Returns:
            Original CEK (32 bytes)
        """

        if len(kek) != 32:
            raise ValueError("KEK must be 32 bytes")

        aesgcm = AESGCM(kek)

        ciphertext = wrapped_cek + tag

        cek = aesgcm.decrypt(nonce, ciphertext, aad)
        return cek
