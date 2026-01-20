# image_encryption/config/kyber_key_setup.py

from image_encryption.crypto.kyber_kem import KyberKEM
from image_encryption.config.kyber_config import KYBER_PUBLIC_KEY_FILE
from hsm.key_store import KeyStore


def setup_kyber_keys():
    """
    One-time Kyber keypair generation and storage.
    """
    ks = KeyStore()

    keys = KyberKEM.generate_keypair()

    # Store secret key securely in HSM / key store
    ks.store_kyber_secret_key(keys["secret_key"])

    # Store public key locally (safe to expose)
    with open(KYBER_PUBLIC_KEY_FILE, "wb") as f:
        f.write(keys["public_key"])

    ks.close()
    print("Kyber keypair setup complete.")


if __name__ == "__main__":
    setup_kyber_keys()
