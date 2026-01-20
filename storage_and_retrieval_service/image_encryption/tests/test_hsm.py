# tests/test_hsm.py
from hsm.key_store import KeyStore


def test_hsm_store_retrieve():
    ks = KeyStore()
    secret = b"super-secret"

    # use test helper that stores non-sensitive, extractable secret
    ks.hsm.store_secret_test("TEST_SECRET", secret)
    retrieved = ks.hsm.retrieve_secret("TEST_SECRET")

    assert retrieved == secret
    ks.close()
