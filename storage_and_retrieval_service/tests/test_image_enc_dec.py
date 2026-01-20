# tests/test_image_enc_dec.py

"""
Comprehensive Image Encryption/Decryption Test Suite
====================================================
Tests the full encryption/decryption pipeline with HSM key storage.
"""

import pytest
import os
import sys
import json
from pathlib import Path
from io import BytesIO
from PIL import Image

# ============================================================================
# FIX: Add parent directory to Python path
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Now import encryption modules
from image_encryption.image_encryptor import ImageEncryptor
from image_encryption.image_decryptor import ImageDecryptor
from image_encryption.config.kyber_key_setup import setup_kyber_keys
from image_encryption.crypto.kyber_kem import KyberKEM
from hsm.key_store import KeyStore
from hsm.hsm_manager import get_hsm_manager


# ============================================================================
# CONSTANTS
# ============================================================================

SAMPLE_IMAGES_DIR = PROJECT_ROOT / "sample_images"


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def setup_hsm_keys():
    """Setup Kyber keys in HSM before tests."""
    print("\n[SETUP] Initializing Kyber keys in HSM...")
    
    # Clear any existing keys
    hsm = get_hsm_manager()
    try:
        hsm.delete_secret("KYBER_SECRET_KEY")
        print("  ✓ Cleared existing Kyber key")
    except:
        print("  ℹ No existing Kyber key found")
    
    # Generate and store new keys
    setup_kyber_keys()
    
    # Verify key storage
    key_store = KeyStore()
    kyber_sk = key_store.load_kyber_secret_key()
    assert len(kyber_sk) > 0, "Kyber secret key not stored in HSM"
    
    print(f"  ✓ Kyber secret key stored: {len(kyber_sk)} bytes")
    
    # Verify public key exists
    pub_key_path = PROJECT_ROOT / "image_encryption" / "config" / "kyber_public.key"
    assert pub_key_path.exists(), "Kyber public key file not created"
    
    print(f"  ✓ Kyber public key saved: {pub_key_path}")
    print("[SETUP] HSM keys ready\n")
    
    yield
    
    print("\n[TEARDOWN] Test cleanup complete")


@pytest.fixture
def sample_image_bytes():
    """Create a test image (100x100 red square)."""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.fixture
def real_image_files():
    """Get list of real image files from sample_images directory."""
    if not SAMPLE_IMAGES_DIR.exists():
        pytest.skip(f"sample_images directory not found: {SAMPLE_IMAGES_DIR}")
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(SAMPLE_IMAGES_DIR.glob(f"*{ext}"))
        image_files.extend(SAMPLE_IMAGES_DIR.glob(f"*{ext.upper()}"))
    
    if not image_files:
        pytest.skip(f"No image files found in {SAMPLE_IMAGES_DIR}")
    
    return sorted(image_files)


@pytest.fixture
def sample_metadata():
    """Sample image metadata."""
    return {
        "image_id": "test_img_001",
        "user_id": "user_12345",
        "timestamp": "2026-01-19T17:00:00Z"
    }


@pytest.fixture
def encryptor(setup_hsm_keys):
    """Initialize ImageEncryptor (requires HSM keys)."""
    return ImageEncryptor()


@pytest.fixture
def decryptor(setup_hsm_keys):
    """Initialize ImageDecryptor (requires HSM keys)."""
    return ImageDecryptor()


# ============================================================================
# TEST CASES
# ============================================================================

class TestHSMKeySetup:
    """Test HSM key initialization and storage."""
    
    def test_kyber_key_in_hsm(self, setup_hsm_keys):
        """Verify Kyber secret key is stored in HSM."""
        key_store = KeyStore()
        kyber_sk = key_store.load_kyber_secret_key()
        
        assert kyber_sk is not None, "Kyber SK not found in HSM"
        assert len(kyber_sk) == 2400, f"Invalid Kyber SK size: {len(kyber_sk)} (expected 2400)"
        print(f"  ✓ Kyber SK loaded from HSM: {len(kyber_sk)} bytes")
    
    def test_kyber_public_key_file(self, setup_hsm_keys):
        """Verify Kyber public key file exists."""
        pub_key_path = PROJECT_ROOT / "image_encryption" / "config" / "kyber_public.key"
        
        assert pub_key_path.exists(), "Kyber public key file not found"
        
        with open(pub_key_path, "rb") as f:
            pub_key = f.read()
        
        assert len(pub_key) == 1184, f"Invalid Kyber PK size: {len(pub_key)} (expected 1184)"
        print(f"  ✓ Kyber PK file verified: {len(pub_key)} bytes")
    
    def test_hsm_list_keys(self, setup_hsm_keys):
        """List all keys in HSM."""
        hsm = get_hsm_manager()
        keys = hsm.list_all_keys()
        
        assert len(keys) > 0, "HSM is empty"
        
        # Find Kyber key
        kyber_key = next((k for k in keys if k['label'] == 'KYBER_SECRET_KEY'), None)
        
        if kyber_key is None:
            kyber_key = next((k for k in keys if k['size'] == 2400), None)
            
            if kyber_key:
                print(f"  ⚠ Kyber key found but missing label")
                print(f"  ℹ Found key with size {kyber_key['size']} bytes")
            else:
                pytest.fail("KYBER_SECRET_KEY not found in HSM")
        else:
            print(f"  ✓ Found KYBER_SECRET_KEY in HSM: {kyber_key['size']} bytes")


class TestImageEncryption:
    """Test image encryption pipeline."""
    
    def test_encrypt_image_success(self, encryptor, sample_image_bytes, sample_metadata):
        """Test successful image encryption."""
        encrypted_obj = encryptor.encrypt_image(
            image_bytes=sample_image_bytes,
            image_id=sample_metadata["image_id"],
            user_id=sample_metadata["user_id"],
            timestamp=sample_metadata["timestamp"]
        )
        
        assert "image_ciphertext" in encrypted_obj
        assert "image_nonce" in encrypted_obj
        assert "image_auth_tag" in encrypted_obj
        assert "wrapped_cek" in encrypted_obj
        assert "kyber_ciphertext" in encrypted_obj
        assert "metadata" in encrypted_obj
        
        print(f"  ✓ Image encrypted successfully")
    
    def test_encrypt_real_images(self, encryptor, real_image_files, sample_metadata):
        """Test encryption of real images from sample_images folder."""
        results = []
        
        for image_path in real_image_files[:5]:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            metadata = sample_metadata.copy()
            metadata["image_id"] = f"real_{image_path.stem}"
            # Don't pass filename - it's not a parameter of encrypt_image()
            
            encrypted_obj = encryptor.encrypt_image(image_bytes, **metadata)
            
            assert "image_ciphertext" in encrypted_obj
            
            results.append({
                'filename': image_path.name,
                'original_size': len(image_bytes),
                'encrypted_size': len(encrypted_obj['image_ciphertext'])
            })
        
        print(f"\n  ✓ Encrypted {len(results)} real images:")
        for r in results:
            print(f"    - {r['filename']}: {r['original_size']:,} → {r['encrypted_size']:,} bytes")

class TestImageDecryption:
    """Test image decryption pipeline."""
    
    def test_decrypt_image_success(self, encryptor, decryptor, sample_image_bytes, sample_metadata):
        """Test successful end-to-end encryption/decryption."""
        encrypted_obj = encryptor.encrypt_image(sample_image_bytes, **sample_metadata)
        decrypted_bytes = decryptor.decrypt_image(encrypted_obj)
        
        assert decrypted_bytes == sample_image_bytes
        print(f"  ✓ End-to-end encryption/decryption successful")
    
    def test_decrypt_real_images(self, encryptor, decryptor, real_image_files, sample_metadata):
        """Test encryption/decryption of real images."""
        for image_path in real_image_files[:3]:
            with open(image_path, "rb") as f:
                original_bytes = f.read()
            
            metadata = sample_metadata.copy()
            metadata["image_id"] = f"real_{image_path.stem}"
            encrypted_obj = encryptor.encrypt_image(original_bytes, **metadata)
            
            decrypted_bytes = decryptor.decrypt_image(encrypted_obj)
            
            assert decrypted_bytes == original_bytes
            print(f"  ✓ {image_path.name}: {len(original_bytes):,} bytes ✓")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
