# image_encryption/tests/test_aes_gcm.py
from image_encryption.crypto.aes_gcm import AESGCMEncryptor
from image_encryption.crypto.csprng import CSPRNG

def test_aes_gcm_encrypt_decrypt():
    data = b"test-image-bytes"
    cek = CSPRNG.generate_cek()
    nonce = CSPRNG.generate_nonce()

    aad = {"image_id": "1", "user_id": "u1", "timestamp": "now"}

    enc = AESGCMEncryptor.encrypt(data, cek, nonce, aad)
    dec = AESGCMEncryptor.decrypt(
        enc["ciphertext"],
        enc["auth_tag"],
        cek,
        nonce,
        aad
    )
    
    assert dec == data
