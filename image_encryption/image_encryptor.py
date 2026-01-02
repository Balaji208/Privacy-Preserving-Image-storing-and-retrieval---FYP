# image_encryption/image_encryptor.py

import base64
from typing import Dict

from image_encryption.crypto.csprng import CSPRNG
from image_encryption.crypto.aes_gcm import AESGCMEncryptor
from image_encryption.crypto.kyber_kem import KyberKEM
from image_encryption.crypto.hkdf_kek import HKDFKEK
from image_encryption.crypto.cek_wrap import CEKWrapper

from hsm.key_store import KeyStore


class ImageEncryptor:
    """
    Main Image Encryption Orchestrator

    Flow:
    1. Generate CEK + nonce
    2. Encrypt image using AES-256-GCM
    3. Kyber encapsulation (PQC)
    4. Derive KEK using HKDF
    5. Wrap CEK (Envelope Encryption)
    6. Return encrypted JSON object
    """

    def __init__(self):
        self.key_store = KeyStore()

    def encrypt_image(self,image_bytes: bytes, image_id: str, user_id: str, timestamp: str) -> Dict:
        """
        Encrypt a plain image and return encrypted object

        Args:
            image_bytes : Raw image bytes
            image_id    : Unique image identifier
            user_id     : Owner/user identifier
            timestamp   : Time of upload

        Returns:
            Encrypted image object (dict)
        """

        # --------------------------------------------------
        # 1️. Generate CEK + Nonce + AAD
        # --------------------------------------------------
        cek = CSPRNG.generate_cek()
        image_nonce = CSPRNG.generate_nonce()

        aad_dict = {
            "image_id": image_id,
            "user_id": user_id,
            "timestamp": timestamp
        }

        # --------------------------------------------------
        # 2️. Encrypt Image using AES-GCM
        # --------------------------------------------------
        image_enc = AESGCMEncryptor.encrypt(
            plaintext_bytes=image_bytes,
            cek=cek,
            nonce=image_nonce,
            aad_dict = aad_dict
        )


        # --------------------------------------------------
        # 3️. Kyber Encapsulation (PQC)
        # --------------------------------------------------
        # Load Kyber public key
        with open("image_encryption/config/kyber_public.key", "rb") as f:
            kyber_pk = f.read()

        kem_result = KyberKEM.encapsulate(kyber_pk)
        kyber_ct = kem_result["ciphertext"]
        shared_secret = kem_result["shared_secret"]

        # --------------------------------------------------
        # 4️. HKDF → Derive KEK
        # --------------------------------------------------
        salt = CSPRNG.generate_salt()

        kek = HKDFKEK.derive_kek(
            shared_secret=shared_secret,
            salt=salt,
            info=b"IMAGE-CEK-WRAPPING"
        )
        # --------------------------------------------------
        # 5️. Wrap CEK (Envelope Encryption)
        # --------------------------------------------------
        wrapped = CEKWrapper.wrap_cek(
            cek=cek,
            kek=kek,
            aad=b"CEK-WRAP-AAD"
        )
        # --------------------------------------------------
        # 6️. Build Final Encrypted Object (JSON-ready)
        # --------------------------------------------------
        encrypted_object = {
            "image_ciphertext": base64.b64encode(image_enc["ciphertext"]).decode(),
            "image_nonce": base64.b64encode(image_nonce).decode(),
            "image_auth_tag": base64.b64encode(image_enc["auth_tag"]).decode(),

            "wrapped_cek": base64.b64encode(wrapped["wrapped_cek"]).decode(),
            "cek_nonce": base64.b64encode(wrapped["nonce"]).decode(),
            "cek_auth_tag": base64.b64encode(wrapped["tag"]).decode(),

            "kyber_ciphertext": base64.b64encode(kyber_ct).decode(),
            "hkdf_salt": base64.b64encode(salt).decode(),
            "metadata": {
                "image_id": image_id,
                "user_id": user_id,
                "timestamp": timestamp,
                "encryption": "AES-256-GCM",
                "kem": "Kyber-ML-KEM",
                "kdf": "HKDF-SHA256"
            }
        }
        return encrypted_object
