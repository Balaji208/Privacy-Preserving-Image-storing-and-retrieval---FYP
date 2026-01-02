# crypto/aes_gcm.py

import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESGCMEncryptor:
    """
    AES-256-GCM Image Encryption / Decryption Module
    Provides confidentiality + integrity
    """

    TAG_LENGTH = 16  # 128-bit authentication tag (GCM standard)

    @staticmethod
    def encrypt( plaintext_bytes: bytes, cek: bytes, nonce: bytes,aad_dict: dict) -> dict:
        """
        Encrypt image bytes using AES-256-GCM

        Args:
            plaintext_bytes : Raw image bytes
            cek             : 256-bit Content Encryption Key
            nonce           : 96-bit nonce
            aad_dict        : AAD metadata (img_id, timestamp, user_id)

        Returns:
            Dictionary containing ciphertext, auth_tag, nonce, aad
        """

        # ---- Validation ----
        if len(cek) != 32:
            raise ValueError("CEK must be 256 bits (32 bytes)")
        if len(nonce) != 12:
            raise ValueError("Nonce must be 96 bits (12 bytes)")

        # ---- Prepare AAD ----
        aad = json.dumps(aad_dict, sort_keys=True).encode("utf-8")

        # ---- AES-GCM Encryption ----
        aesgcm = AESGCM(cek)

        ciphertext_with_tag = aesgcm.encrypt(
            nonce=nonce,
            data=plaintext_bytes,
            associated_data=aad
        )

        # ---- Split Ciphertext and Tag ----
        ciphertext = ciphertext_with_tag[:-AESGCMEncryptor.TAG_LENGTH]
        auth_tag = ciphertext_with_tag[-AESGCMEncryptor.TAG_LENGTH:]

        return { "ciphertext": ciphertext, "auth_tag": auth_tag, "nonce": nonce, "aad": aad_dict }

    @staticmethod
    def decrypt(ciphertext: bytes, auth_tag: bytes, cek: bytes, nonce: bytes, aad_dict: dict) -> bytes:
        """
        Decrypt AES-256-GCM encrypted image

        Args:
            ciphertext : Encrypted image bytes
            auth_tag   : 128-bit authentication tag
            cek        : 256-bit Content Encryption Key
            nonce      : 96-bit nonce
            aad_dict   : AAD metadata used during encryption

        Returns:
            Decrypted image bytes
        """

        # ---- Validation ----
        if len(cek) != 32:
            raise ValueError("CEK must be 256 bits (32 bytes)")
        if len(nonce) != 12:
            raise ValueError("Nonce must be 96 bits (12 bytes)")
        if len(auth_tag) != 16:
            raise ValueError("Auth tag must be 128 bits (16 bytes)")

        # ---- Prepare AAD ----
        aad = json.dumps(aad_dict, sort_keys=True).encode("utf-8")

        # ---- AES-GCM Decryption ----
        aesgcm = AESGCM(cek)

        plaintext = aesgcm.decrypt(
            nonce=nonce,
            data=ciphertext + auth_tag,
            associated_data=aad
        )

        return plaintext


