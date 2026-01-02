# hsm/key_store.py

from hsm.hsm_manager import get_hsm_manager


class KeyStore:
    """
    High-level abstraction for HSM storage
    """

    def __init__(self):
        self.hsm = get_hsm_manager()

    def store_kyber_secret_key(self, sk: bytes):
        print("[KeyStore] Storing Kyber SK in HSM")
        self.hsm.store_secret_test("KYBER_SECRET_KEY", sk)

    def load_kyber_secret_key(self) -> bytes:
        return self.hsm.retrieve_secret("KYBER_SECRET_KEY")

    def close(self):
        # Do not close the singleton session here
        pass
