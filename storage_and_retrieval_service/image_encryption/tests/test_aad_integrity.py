import json
import base64
from pathlib import Path
from cryptography.exceptions import InvalidTag  # Add this import

import pytest

from image_encryption.crypto.aes_gcm import AESGCMEncryptor
from image_encryption.crypto.kyber_kem import KyberKEM
from image_encryption.crypto.hkdf_kek import HKDFKEK
from image_encryption.crypto.cek_wrap import CEKWrapper
from hsm.key_store import KeyStore


ENCRYPTED_JSON_PATH = Path("image_encryption/data/encrypted_outputs/encrypted_image.json")

# Output files for each test case
OUT_VALID = Path("image_encryption/data/encrypted_outputs/test1_valid_image.jpg")
OUT_AAD_TAMPER = Path("image_encryption/data/encrypted_outputs/test2_aad_tamper.bin")
OUT_CT_TAMPER = Path("image_encryption/data/encrypted_outputs/test3_ct_tamper.bin")


def _decrypt_test_case(tamper_type: str = "none", save_output: bool = False):
    """Core decryption function with different tamper modes."""
    
    # 1) Load encrypted JSON
    with open(ENCRYPTED_JSON_PATH, "r", encoding="utf-8") as f:
        enc = json.load(f)

    # 2) Decode base64 fields
    cipher_image = base64.b64decode(enc["image_ciphertext"])
    image_nonce = base64.b64decode(enc["image_nonce"])
    image_auth_tag = base64.b64decode(enc["image_auth_tag"])

    wrapped_cek = base64.b64decode(enc["wrapped_cek"])
    cek_nonce = base64.b64decode(enc["cek_nonce"])
    cek_auth_tag = base64.b64decode(enc["cek_auth_tag"])

    kyber_ct = base64.b64decode(enc["kyber_ciphertext"])
    salt = base64.b64decode(enc["hkdf_salt"])

    meta = enc["metadata"]

    # AAD used at encrypt time: only these three fields
    aad = {
        "image_id": meta["image_id"],
        "user_id": meta["user_id"],
        "timestamp": meta["timestamp"],
    }

    # Apply tamper based on test case
    if tamper_type == "aad":
        aad = dict(aad)
        aad["user_id"] = "ATTACKER"
        print("🔒 TEST CASE 2: AAD Tampered (user_id → ATTACKER)")
    elif tamper_type == "ct":
        # Flip one bit in ciphertext
        cipher_image = bytearray(cipher_image)
        cipher_image[0] ^= 0x01  # Flip LSB of first byte
        cipher_image = bytes(cipher_image)
        print("🔒 TEST CASE 3: Ciphertext Tampered (bit flip in byte 0)")
    else:
        print("✅ TEST CASE 1: VALID - No tampering")

    # 3-5) Kyber → HKDF → CEK unwrap
    ks = KeyStore()
    kyber_sk = ks.load_kyber_secret_key()
    shared_secret = KyberKEM.decapsulate(ciphertext=kyber_ct, secret_key=kyber_sk)

    kek = HKDFKEK.derive_kek(shared_secret=shared_secret, salt=salt, info=b"IMAGE-CEK-WRAPPING")

    cek = CEKWrapper.unwrap_cek(
        wrapped_cek=wrapped_cek,
        nonce=cek_nonce,
        tag=cek_auth_tag,
        kek=kek,
        aad=b"CEK-WRAP-AAD",
    )

    # 6) AES-GCM decrypt (fails on tampering)
    plaintext_image = AESGCMEncryptor.decrypt(
        ciphertext=cipher_image,
        auth_tag=image_auth_tag,
        cek=cek,
        nonce=image_nonce,
        aad_dict=aad,
    )

    # 7) Save output files
    if save_output:
        if tamper_type == "none":
            OUT_VALID.write_bytes(plaintext_image)
            print(f"   ✅ SAVED: {OUT_VALID}")
        elif tamper_type == "aad":
            OUT_AAD_TAMPER.write_bytes(plaintext_image)
            print(f"   🔒 SAVED: {OUT_AAD_TAMPER}")
        elif tamper_type == "ct":
            OUT_CT_TAMPER.write_bytes(plaintext_image)
            print(f"   🔒 SAVED: {OUT_CT_TAMPER}")

    return plaintext_image


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    pass


def test_case_1_valid_no_tamper():
    """TEST CASE 1: Valid decryption → Perfect image"""
    img = _decrypt_test_case(tamper_type="none", save_output=True)
    assert isinstance(img, (bytes, bytearray))
    assert len(img) > 1000
    print("🎉 TEST CASE 1 PASSED: Valid image decrypted ✓")


def test_case_2_aad_tamper_detected():
    """TEST CASE 2: AAD tampering → Integrity failure"""
    with pytest.raises(InvalidTag):  # Specific exception type
        _decrypt_test_case(tamper_type="aad", save_output=False)
    print("🎉 TEST CASE 2 PASSED: AAD tampering DETECTED ✓")


def test_case_3_ciphertext_tamper_detected():
    """TEST CASE 3: Ciphertext tampering → Integrity failure"""
    with pytest.raises(InvalidTag):  # Specific exception type
        _decrypt_test_case(tamper_type="ct", save_output=False)
    print("🎉 TEST CASE 3 PASSED: Ciphertext tampering DETECTED ✓")
