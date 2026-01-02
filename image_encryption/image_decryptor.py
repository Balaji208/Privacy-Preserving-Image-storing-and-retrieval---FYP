# image_encryption/image_decryptor.py

import base64
from typing import Dict

from image_encryption.crypto.aes_gcm import AESGCMEncryptor
from image_encryption.crypto.kyber_kem import KyberKEM
from image_encryption.crypto.hkdf_kek import HKDFKEK
from image_encryption.crypto.cek_wrap import CEKWrapper
from hsm.key_store import KeyStore


class ImageDecryptor:
    """
    Image Decryption Orchestrator

    Reverse Flow:
    1. Load encrypted object
    2. Kyber decapsulation (HSM / SoftHSM)
    3. HKDF → derive KEK
    4. Unwrap CEK
    5. AES-GCM decrypt image
    """

    def __init__(self):
        self.key_store = KeyStore()

    def decrypt_image(self, enc_obj: Dict) -> bytes:
        """
        Decrypt encrypted image object and return original image bytes.
        """
        # Debug: list everything on the token
        self.key_store.hsm.debug_list_objects()

        kyber_sk = self.key_store.load_kyber_secret_key()
        # -------------------------------
        # Decode Base64 fields
        # -------------------------------
        image_ciphertext = base64.b64decode(enc_obj["image_ciphertext"])
        image_nonce = base64.b64decode(enc_obj["image_nonce"])
        image_tag = base64.b64decode(enc_obj["image_auth_tag"])

        wrapped_cek = base64.b64decode(enc_obj["wrapped_cek"])
        cek_nonce = base64.b64decode(enc_obj["cek_nonce"])
        cek_tag = base64.b64decode(enc_obj["cek_auth_tag"])

        kyber_ct = base64.b64decode(enc_obj["kyber_ciphertext"])
        salt = base64.b64decode(enc_obj["hkdf_salt"])

        meta = enc_obj["metadata"]
        image_id = meta["image_id"]
        user_id = meta["user_id"]
        timestamp = meta["timestamp"]

        # AAD must match the format used in ImageEncryptor
        aad = f"{image_id}|{user_id}|{timestamp}".encode("utf-8")

        # -------------------------------
        # 1) Kyber Decapsulation (HSM)
        # -------------------------------
        kyber_sk = self.key_store.load_kyber_secret_key()
        shared_secret = KyberKEM.decapsulate(
            ciphertext=kyber_ct,
            secret_key=kyber_sk,
        )

        # -------------------------------
        # 2) HKDF → Derive KEK
        # -------------------------------
        kek = HKDFKEK.derive_kek(
            shared_secret=shared_secret,
            salt=salt,
            info=b"IMAGE-CEK-WRAPPING",
        )

        # -------------------------------
        # 3) Unwrap CEK
        # -------------------------------
        cek = CEKWrapper.unwrap_cek(
            wrapped_cek=wrapped_cek,
            nonce=cek_nonce,
            tag=cek_tag,
            kek=kek,
            aad=b"CEK-WRAP-AAD",
        )

        # 4) AES-GCM Image Decryption
        plaintext_image = AESGCMEncryptor.decrypt(
            ciphertext=image_ciphertext,
            auth_tag=image_tag,       
            cek=cek,
            nonce=image_nonce,
            aad_dict={                         
                "image_id": image_id,
                "user_id": user_id,
                "timestamp": timestamp,
            },
        )
        
        return plaintext_image
