"""
LSH Unit Tests
==============
Comprehensive unit tests for LSH tokenization module.
"""

import pytest
import redis
import numpy as np
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lsh_tokenization import LSHIndexer, LSHConfig
from lsh_tokenization.setup import ImageHashID, ImageHashMetadata, LSHImageIndexer
from lsh_tokenization.utils.security import SecurityUtils

# Check if HSM is available
try:
    from lsh_tokenization.setup import LSHKeySetup, quick_setup
    HSM_AVAILABLE = True
except:
    HSM_AVAILABLE = False
    print("⚠ HSM not available, using direct key generation for tests")


@pytest.fixture
def redis_client():
    """Fixture for Redis client."""
    client = redis.Redis(host='localhost', port=6379, db=15)  # Use db 15 for testing
    yield client
    # Cleanup
    client.flushdb()


@pytest.fixture
def hmac_key():
    """Fixture for HMAC key."""
    if HSM_AVAILABLE:
        try:
            return LSHKeySetup.initialize_hmac_key()
        except:
            pass
    # Fallback: generate key directly
    return SecurityUtils.generate_hmac_key()


@pytest.fixture
def lsh_indexer(redis_client, hmac_key):
    """Fixture for LSH indexer."""
    config = LSHConfig(
        hash_length=256,
        num_tables=6,
        bits_per_table=12,
        random_seed=42
    )
    return LSHIndexer(redis_client, hmac_key, config)


@pytest.fixture
def image_indexer(lsh_indexer):
    """Fixture for image indexer."""
    return LSHImageIndexer(lsh_indexer)


class TestLSHSetup:
    """Test LSH setup functionality."""
    
    @pytest.mark.skipif(not HSM_AVAILABLE, reason="HSM not available")
    def test_hmac_key_initialization(self):
        """Test HMAC key initialization."""
        key = LSHKeySetup.initialize_hmac_key()
        assert len(key) == 32, "HMAC key should be 32 bytes"
        assert isinstance(key, bytes), "HMAC key should be bytes"
    
    @pytest.mark.skipif(not HSM_AVAILABLE, reason="HSM not available")
    def test_setup_verification(self):
        """Test setup verification."""
        status = LSHKeySetup.verify_setup()
        assert isinstance(status, dict), "Status should be dict"
        assert 'hsm_available' in status
        assert 'hmac_key_exists' in status
        assert 'key_valid' in status


class TestImageHashID:
    """Test ImageHashID functionality."""
    
    def test_generate_hash_id(self):
        """Test hash_id generation."""
        hash_id = ImageHashID.generate("IMG_001", datetime.now())
        assert len(hash_id) == 16, "Short hash_id should be 16 chars"
        assert ImageHashID.validate(hash_id), "Generated hash_id should be valid"
    
    def test_generate_from_path(self):
        """Test hash_id generation from path."""
        image_id, hash_id = ImageHashID.generate_from_path(
            Path("./test_image.jpg")
        )
        assert image_id == "test_image"
        assert len(hash_id) == 16
    
    def test_validate_hash_id(self):
        """Test hash_id validation."""
        # Valid hash_ids
        assert ImageHashID.validate("a3f5b2c1d8e9f012")
        assert ImageHashID.validate("a" * 64)
        
        # Invalid hash_ids
        assert not ImageHashID.validate("invalid")
        assert not ImageHashID.validate("12345")
        assert not ImageHashID.validate("gg" * 8)


class TestImageHashMetadata:
    """Test metadata management."""
    
    def test_add_and_get_metadata(self, tmp_path):
        """Test adding and retrieving metadata."""
        metadata = ImageHashMetadata(storage_path=tmp_path / "test_metadata.json")
        
        metadata.add(
            hash_id="test_hash_123",
            image_id="IMG_001",
            tenant_id="test_tenant",
            patient_id="P001"
        )
        
        result = metadata.get("test_hash_123")
        assert result is not None
        assert result['image_id'] == "IMG_001"
        assert result['patient_id'] == "P001"
    
    def test_search_by_image_id(self, tmp_path):
        """Test searching by image_id."""
        metadata = ImageHashMetadata(storage_path=tmp_path / "test_metadata.json")
        
        # Add multiple entries for same image
        for i in range(3):
            metadata.add(
                hash_id=f"hash_{i}",
                image_id="IMG_001",
                tenant_id="test_tenant"
            )
        
        results = metadata.search_by_image_id("IMG_001")
        assert len(results) == 3
    
    def test_save_and_load(self, tmp_path):
        """Test save and load functionality."""
        storage_path = tmp_path / "test_metadata.json"
        
        # Create and save
        metadata1 = ImageHashMetadata(storage_path=storage_path)
        metadata1.add(
            hash_id="test_hash",
            image_id="IMG_001",
            tenant_id="test_tenant"
        )
        metadata1.save()
        
        # Load in new instance
        metadata2 = ImageHashMetadata(storage_path=storage_path)
        result = metadata2.get("test_hash")
        assert result is not None
        assert result['image_id'] == "IMG_001"


class TestLSHIndexer:
    """Test LSH indexer functionality."""
    
    def test_add_and_query(self, lsh_indexer):
        """Test basic add and query."""
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        
        # Add
        success = lsh_indexer.add(binary_hash, "test_tenant", "hash_001")
        assert success
        
        # Query
        candidates = lsh_indexer.query(binary_hash, "test_tenant")
        assert "hash_001" in candidates
    
    def test_batch_add(self, lsh_indexer):
        """Test batch adding."""
        entries = []
        for i in range(10):
            binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
            entries.append({
                'binary_hash': binary_hash,
                'tenant_id': 'test_tenant',
                'hash_id': f'hash_{i:03d}'
            })
        
        stats = lsh_indexer.add_batch(entries)
        assert stats['successful'] == 10
        assert stats['failed'] == 0
    
    def test_tenant_isolation(self, lsh_indexer):
        """Test tenant isolation."""
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        
        # Add to tenant_A
        lsh_indexer.add(binary_hash, "tenant_A", "hash_A")
        
        # Query tenant_B (should get nothing)
        candidates_b = lsh_indexer.query(binary_hash, "tenant_B")
        assert "hash_A" not in candidates_b
        
        # Query tenant_A (should get hash)
        candidates_a = lsh_indexer.query(binary_hash, "tenant_A")
        assert "hash_A" in candidates_a
    
    def test_stats(self, lsh_indexer):
        """Test statistics."""
        # Add some hashes
        for i in range(5):
            binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
            lsh_indexer.add(binary_hash, "test_tenant", f"hash_{i}")
        
        stats = lsh_indexer.get_stats()
        assert 'redis' in stats
        assert stats['redis']['total_hash_ids'] >= 5


class TestLSHImageIndexer:
    """Test image indexer functionality."""
    
    def test_add_image(self, image_indexer):
        """Test adding image."""
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        
        success, hash_id = image_indexer.add_image(
            binary_hash=binary_hash,
            image_id="IMG_001",
            tenant_id="test_tenant",
            patient_id="P001"
        )
        
        assert success
        assert len(hash_id) == 16
        
        # Check metadata
        metadata = image_indexer.metadata.get(hash_id)
        assert metadata is not None
        assert metadata['image_id'] == "IMG_001"
        assert metadata['patient_id'] == "P001"
    
    def test_query_image(self, image_indexer):
        """Test querying images."""
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        
        # Add image
        success, hash_id = image_indexer.add_image(
            binary_hash=binary_hash,
            image_id="IMG_001",
            tenant_id="test_tenant"
        )
        
        # Query
        results = image_indexer.query_image(
            binary_hash=binary_hash,
            tenant_id="test_tenant",
            return_metadata=True
        )
        
        assert len(results) > 0
        assert any(r['hash_id'] == hash_id for r in results)
    
    def test_get_image_info(self, image_indexer):
        """Test getting image info."""
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        
        # Add image
        image_indexer.add_image(
            binary_hash=binary_hash,
            image_id="IMG_001",
            tenant_id="test_tenant"
        )
        
        # Get info
        info = image_indexer.get_image_info("IMG_001")
        assert len(info) > 0
        assert info[0]['image_id'] == "IMG_001"


class TestQuickSetup:
    """Test quick setup functionality."""
    
    @pytest.mark.skipif(not HSM_AVAILABLE, reason="HSM not available")
    def test_quick_setup(self, redis_client):
        """Test quick setup."""
        lsh_indexer, image_indexer = quick_setup(redis_client)
        
        assert lsh_indexer is not None
        assert image_indexer is not None
        
        # Test basic functionality
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        success, hash_id = image_indexer.add_image(
            binary_hash=binary_hash,
            image_id="TEST_IMG",
            tenant_id="test"
        )
        assert success


def test_end_to_end_workflow(redis_client, hmac_key):
    """End-to-end workflow test."""
    # Setup manually without HSM
    config = LSHConfig(
        hash_length=256,
        num_tables=6,
        bits_per_table=12,
        random_seed=42
    )
    
    lsh_indexer = LSHIndexer(redis_client, hmac_key, config)
    image_indexer = LSHImageIndexer(lsh_indexer)
    
    # Add images
    images = []
    for i in range(10):
        binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        success, hash_id = image_indexer.add_image(
            binary_hash=binary_hash,
            image_id=f"IMG_{i:03d}",
            tenant_id="hospital_A",
            patient_id=f"P{1000+i}"
        )
        assert success
        images.append((binary_hash, hash_id))
    
    # Query
    query_hash, query_hash_id = images[0]
    results = image_indexer.query_image(query_hash, "hospital_A")
    
    # Verify
    assert len(results) > 0
    assert any(r['hash_id'] == query_hash_id for r in results)
    
    # Save metadata
    image_indexer.save_metadata()
    
    # Get stats
    stats = image_indexer.get_stats()
    assert stats['metadata']['total_entries'] >= 10
    
    print("\n✓ End-to-end workflow test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
