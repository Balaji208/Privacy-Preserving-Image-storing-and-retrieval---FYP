# image_encryption/tests/test_Kyber_KEM.py
from image_encryption.crypto.kyber_kem import KyberKEM

def test_kyber_kem():
    kp = KyberKEM.generate_keypair()
    enc = KyberKEM.encapsulate(kp["public_key"])
    ss = KyberKEM.decapsulate(enc["ciphertext"], kp["secret_key"])

    assert enc["shared_secret"] == ss
