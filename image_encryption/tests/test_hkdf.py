# image_encryption/tests/test_hkdf.py
from image_encryption.crypto.hkdf_kek import HKDFKEK
from image_encryption.crypto.csprng import CSPRNG

def test_hkdf_kek():
    ss = CSPRNG.generate_cek()
    salt = CSPRNG.generate_salt()

    kek1 = HKDFKEK.derive_kek(ss, salt)
    kek2 = HKDFKEK.derive_kek(ss, salt)

    assert kek1 == kek2
