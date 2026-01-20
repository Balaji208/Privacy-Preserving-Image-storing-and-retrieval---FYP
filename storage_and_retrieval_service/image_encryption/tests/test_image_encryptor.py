# image_encryption/tests/test_image_encryptor.py

from image_encryption.image_encryptor import ImageEncryptor
from image_encryption.utils.image_io import read_image_bytes

def test_full_image_encryption():
    encryptor = ImageEncryptor()

    image_bytes = read_image_bytes(
        "image_encryption/data/input_images/sample.jpg"
    )

    enc = encryptor.encrypt_image(
        image_bytes=image_bytes,
        image_id="img123",
        user_id="user1",
        timestamp="2025-01-01T10:00:00"
    )

    # Validate required fields
    required = [
        "image_ciphertext",
        "image_nonce",
        "image_auth_tag",
        "wrapped_cek",
        "cek_nonce",
        "cek_auth_tag",
        "kyber_ciphertext",
        "hkdf_salt",
        "metadata"
    ]

    for key in required:
        assert key in enc
