# pip install cryptography
# crypto/hkdf_kek.py

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


class HKDFKEK:
    """
    HKDF-Based Key Encryption Key (KEK) Derivation Module

    Input:
        - Shared Secret (SS) from Kyber KEM
        - Random Salt (per image)
        - Contextual Info string

    Output:
        - KEK (256-bit AES key)
    """

    @staticmethod
    def derive_kek(
        shared_secret: bytes,
        salt: bytes,
        info: bytes = b"CEK-WRAPPING-KEY"
    ) -> bytes:
        """
        Derive a 256-bit KEK using HKDF (SHA-256)

        Args:
            shared_secret : Kyber shared secret (SS)
            salt          : Random salt (stored or transmitted)
            info          : Contextual domain separation string

        Returns:
            KEK (32 bytes)
        """

        if not isinstance(shared_secret, (bytes, bytearray)):
            raise TypeError("Shared secret must be bytes")

        if not isinstance(salt, (bytes, bytearray)):
            raise TypeError("Salt must be bytes")

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,            # 256-bit KEK
            salt=salt,
            info=info,
        )

        kek = hkdf.derive(shared_secret)
        return kek
