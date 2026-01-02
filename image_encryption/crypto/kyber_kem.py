# pip install pqcrypto
# crypto/kyber_kem.py

from pqcrypto.kem import ml_kem_768


class KyberKEM:
    """
    Post-Quantum Key Encapsulation Module (ML-KEM / Kyber)

    Responsibilities:
    - Generate Kyber public/private keypair
    - Encapsulate shared secret (encryption side)
    - Decapsulate shared secret (decryption side)

    Used for:
    - Secure CEK wrapping (via HKDF + AES-GCM)
    """

    @staticmethod
    def generate_keypair() -> dict:
        """
        Generate Kyber (ML-KEM) keypair.

        Returns:
            {
                "public_key": bytes,
                "secret_key": bytes
            }
        """
        public_key, secret_key = ml_kem_768.generate_keypair()

        return {
            "public_key": public_key,
            "secret_key": secret_key,
        }

    @staticmethod
    def encapsulate(public_key: bytes) -> dict:
        """
        Kyber Encapsulation (Encryption side).

        Input:
            public_key : Kyber public key

        Output:
            {
                "ciphertext": CT,
                "shared_secret": SS
            }
        """
        ciphertext, shared_secret = ml_kem_768.encrypt(public_key)

        return {
            "ciphertext": ciphertext,
            "shared_secret": shared_secret,
        }

    @staticmethod
    def decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes:
        """
        Kyber Decapsulation (Decryption side).

        Input:
            ciphertext : Kyber ciphertext (CT)
            secret_key : Kyber secret key (stored in SoftHSM)

        Output:
            shared_secret (SS)
        """
        # pqcrypto expects (secret_key, ciphertext)
        shared_secret = ml_kem_768.decrypt(secret_key, ciphertext)
        return shared_secret
