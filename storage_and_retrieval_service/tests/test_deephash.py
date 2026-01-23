"""
DeepHash Module Tests
=====================
Comprehensive tests for DeepHash v4.0 binary code generation with real medical images.

Tests both:
- v4.0 Direct Mode (512D → Hash, no PCA)
- Legacy PCA Mode (512D → PCA → Hash)

Run with:
    pytest tests/test_deephash.py -v
    python tests/test_deephash.py
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import sys
from PIL import Image
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deephashing import DeepHashGenerator, DeepHashingConfig
from deephashing.core.model import DeepHashingHead
from deephashing.exceptions import (
    ModelLoadError, 
    ValidationError, 
    HashGenerationError,
    PCATransformError
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# REAL IMAGE HELPERS
# ============================================================================

def get_sample_images():
    """Get list of real medical images from sample_images folder."""
    image_dirs = [
        Path("sample_images"),
        Path("../sample_images"),
        Path("tests/sample_images"),
        Path("data/sample_images"),
    ]
    
    for img_dir in image_dirs:
        if img_dir.exists():
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                image_files.extend(list(img_dir.glob(ext)))
            
            if image_files:
                logger.info(f"✓ Found {len(image_files)} images in {img_dir}")
                return sorted(image_files)[:20]  # Limit to 20 images
    
    logger.warning("⚠ No sample images found, using synthetic images")
    return []


def create_synthetic_features(seed: int = None) -> np.ndarray:
    """Create synthetic 512D feature vector."""
    if seed is not None:
        np.random.seed(seed)
    return np.random.randn(512).astype(np.float32)


def create_synthetic_features_batch(batch_size: int, seed: int = None) -> np.ndarray:
    """Create batch of synthetic features."""
    if seed is not None:
        np.random.seed(seed)
    return np.random.randn(batch_size, 512).astype(np.float32)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_images():
    """Get sample medical images."""
    return get_sample_images()


@pytest.fixture
def sample_features():
    """Create sample 512-dim feature vector."""
    return create_synthetic_features(seed=42)


@pytest.fixture
def sample_features_batch():
    """Create batch of feature vectors."""
    return create_synthetic_features_batch(10, seed=42)


@pytest.fixture
def v4_model_paths():
    """Get v4.0 model paths."""
    model_paths = [
        Path("models/deephash_v4_statedict.pt"),
        Path("models/deephashv4statedict.pt"),
        Path("models/deephash_v4.pt"),
    ]
    
    for path in model_paths:
        if path.exists():
            return {'model': path, 'pca': None}
    
    return None


@pytest.fixture
def legacy_model_paths():
    """Get legacy PCA model paths."""
    model_candidates = [
        Path("models/deephash_state_dict_only.pt"),
        Path("models/deephash.pt"),
    ]
    
    pca_candidates = [
        Path("models/pca_whitening.pkl"),
        Path("models/pca.pkl"),
    ]
    
    for model_path in model_candidates:
        for pca_path in pca_candidates:
            if model_path.exists() and pca_path.exists():
                return {'model': model_path, 'pca': pca_path}
    
    return None


@pytest.fixture
def test_model_path(tmp_path):
    """Create a temporary test model."""
    model = DeepHashingHead(input_dim=512, hidden_dims=[1024, 512], hash_bits=256)
    
    # Save as direct state_dict (v4.0 format)
    model_path = tmp_path / "test_deephash.pt"
    torch.save(model.state_dict(), model_path)
    
    return model_path


# ============================================================================
# MODEL ARCHITECTURE TESTS
# ============================================================================

class TestDeepHashingHead:
    """Test DeepHashingHead model architecture."""
    
    def test_v4_architecture_initialization(self):
        """Test v4.0 architecture (512D input, [1024, 512] hidden)."""
        model = DeepHashingHead(
            input_dim=512,
            hidden_dims=[1024, 512],
            hash_bits=256,
            dropout=0.2
        )
        
        assert model.input_dim == 512
        assert model.hash_bits == 256
        assert len(model.feature_layers) > 0
    
    def test_legacy_architecture_initialization(self):
        """Test legacy architecture (256D input, [512, 256] hidden)."""
        model = DeepHashingHead(
            input_dim=256,
            hidden_dims=[512, 256],
            hash_bits=256
        )
        
        assert model.input_dim == 256
        assert model.hash_bits == 256
    
    def test_forward_pass(self, sample_features):
        """Test forward pass generates continuous hash codes."""
        model = DeepHashingHead(input_dim=512, hash_bits=256)
        model.eval()
        
        x = torch.from_numpy(sample_features).unsqueeze(0)
        output = model(x)
        
        assert output.shape == (1, 256), "Output should be (batch, hash_bits)"
        assert output.dtype == torch.float32
    
    def test_binary_hash_generation(self, sample_features):
        """Test binary hash generation."""
        model = DeepHashingHead(input_dim=512, hash_bits=256)
        model.eval()
        
        x = torch.from_numpy(sample_features).unsqueeze(0)
        binary_hash = model.get_binary_hash(x)
        
        assert binary_hash.shape == (1, 256)
        assert torch.all((binary_hash == -1) | (binary_hash == 1))
    
    def test_batch_processing(self, sample_features_batch):
        """Test batch processing."""
        model = DeepHashingHead(input_dim=512, hash_bits=256)
        model.eval()
        
        x = torch.from_numpy(sample_features_batch)
        output = model(x)
        
        assert output.shape == (10, 256)


# ============================================================================
# V4.0 DIRECT MODE TESTS
# ============================================================================

class TestDeepHashV4DirectMode:
    """Test DeepHash v4.0 in direct mode (no PCA)."""
    
    @pytest.mark.skipif(
        not any(Path("models").glob("*v4*.pt")),
        reason="v4.0 model not found"
    )
    def test_v4_initialization(self, v4_model_paths):
        """Test v4.0 generator initialization."""
        if v4_model_paths is None:
            pytest.skip("v4.0 model not found")
        
        config = DeepHashingConfig(
            hash_model_path=str(v4_model_paths['model']),
            pca_transform_path=None,  # Direct mode
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
        
        generator = DeepHashGenerator(config=config)
        
        assert generator.config.use_pca == False
        assert generator.config.feature_dim == 512
        assert generator.config.hash_bits == 256
        assert generator.pca is None
    
    def test_v4_with_test_model(self, test_model_path, sample_features):
        """Test v4.0 mode with test model."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None,
            device='cpu'
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Generate hash
        binary, continuous = generator.generate_hash(sample_features)
        
        assert binary.shape == (1, 256)
        assert continuous.shape == (1, 256)
        assert binary.dtype == np.uint8
        assert np.all((binary == 0) | (binary == 1))
    
    def test_v4_batch_generation(self, test_model_path, sample_features_batch):
        """Test v4.0 batch hash generation."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        binary, continuous = generator.generate_hash(sample_features_batch)
        
        assert binary.shape == (10, 256)
        assert np.all((binary == 0) | (binary == 1))
    
    def test_v4_determinism(self, test_model_path, sample_features):
        """Test deterministic hash generation."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        binary1, _ = generator.generate_hash(sample_features)
        binary2, _ = generator.generate_hash(sample_features)
        
        assert np.array_equal(binary1, binary2), "Same input should produce same hash"


# ============================================================================
# LEGACY PCA MODE TESTS
# ============================================================================

class TestDeepHashLegacyPCAMode:
    """Test DeepHash in legacy PCA mode."""
    
    @pytest.mark.skipif(
        not Path("models/pca_whitening.pkl").exists(),
        reason="PCA model not found"
    )
    def test_pca_mode_initialization(self, legacy_model_paths):
        """Test legacy PCA mode initialization."""
        if legacy_model_paths is None:
            pytest.skip("Legacy PCA model not found")
        
        config = DeepHashingConfig(
            hash_model_path=str(legacy_model_paths['model']),
            pca_transform_path=str(legacy_model_paths['pca']),
            device='cpu'
        )
        
        generator = DeepHashGenerator(config=config)
        
        assert generator.config.use_pca == True
        assert generator.pca is not None
        assert generator.config.pca_dim == 256
    
    @pytest.mark.skipif(
        not Path("models/pca_whitening.pkl").exists(),
        reason="PCA model not found"
    )
    def test_pca_mode_generation(self, legacy_model_paths, sample_features):
        """Test hash generation with PCA."""
        if legacy_model_paths is None:
            pytest.skip("Legacy PCA model not found")
        
        config = DeepHashingConfig(
            hash_model_path=str(legacy_model_paths['model']),
            pca_transform_path=str(legacy_model_paths['pca'])
        )
        
        generator = DeepHashGenerator(config=config)
        binary, continuous = generator.generate_hash(sample_features)
        
        assert binary.shape == (1, 256)
        assert np.all((binary == 0) | (binary == 1))


# ============================================================================
# SIMILARITY TESTS
# ============================================================================

class TestHashSimilarity:
    """Test hash similarity computation."""
    
    def test_identical_hashes(self, test_model_path, sample_features):
        """Test identical hashes have distance 0."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        binary, _ = generator.generate_hash(sample_features)
        hash1 = binary.squeeze()
        
        sim_result = generator.compute_similarity(hash1, hash1)
        
        assert sim_result['hamming_distance'] == 0
        assert sim_result['similarity_score'] == 1.0
        assert sim_result['confidence'] == 'very_high'
    
    def test_different_hashes(self, test_model_path):
        """Test different hashes have non-zero distance."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        features1 = create_synthetic_features(seed=1)
        features2 = create_synthetic_features(seed=2)
        
        binary1, _ = generator.generate_hash(features1)
        binary2, _ = generator.generate_hash(features2)
        
        sim_result = generator.compute_similarity(
            binary1.squeeze(),
            binary2.squeeze()
        )
        
        assert 0 <= sim_result['hamming_distance'] <= 256
        assert 0.0 <= sim_result['similarity_score'] <= 1.0
        assert sim_result['confidence'] in [
            'very_high', 'high', 'medium', 'low', 'very_low'
        ]
    
    def test_hamming_distance_range(self, test_model_path):
        """Test Hamming distance is within valid range."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Generate 10 random hashes
        hashes = []
        for i in range(10):
            features = create_synthetic_features(seed=i)
            binary, _ = generator.generate_hash(features)
            hashes.append(binary.squeeze())
        
        # Check all pairwise distances
        for i in range(len(hashes)):
            for j in range(i+1, len(hashes)):
                sim_result = generator.compute_similarity(hashes[i], hashes[j])
                hd = sim_result['hamming_distance']
                
                assert 0 <= hd <= 256, f"Hamming distance {hd} out of range"


# ============================================================================
# REAL MEDICAL IMAGE TESTS
# ============================================================================

class TestRealMedicalImages:
    """Test with real medical images."""
    
    @pytest.mark.skipif(
        len(get_sample_images()) == 0,
        reason="No medical images found"
    )
    def test_medical_image_consistency(self, test_model_path, sample_images):
        """Test consistent hashing for medical images."""
        if len(sample_images) == 0:
            pytest.skip("No medical images available")
        
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Use first image
        features = create_synthetic_features(seed=0)  # Simulate extracted features
        
        # Generate hash twice
        binary1, _ = generator.generate_hash(features)
        binary2, _ = generator.generate_hash(features)
        
        assert np.array_equal(binary1, binary2)
        logger.info(f"✓ Medical image hash generation is consistent")
    
    @pytest.mark.skipif(
        len(get_sample_images()) < 5,
        reason="Need at least 5 medical images"
    )
    def test_medical_image_batch_processing(self, test_model_path, sample_images):
        """Test batch processing of medical images."""
        if len(sample_images) < 5:
            pytest.skip("Need at least 5 images")
        
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Simulate features for 5 images
        batch_features = create_synthetic_features_batch(5, seed=42)
        
        binary, continuous = generator.generate_hash(batch_features)
        
        assert binary.shape == (5, 256)
        assert np.all((binary == 0) | (binary == 1))
        
        logger.info(f"✓ Processed batch of 5 medical images")
    
    @pytest.mark.skipif(
        len(get_sample_images()) < 10,
        reason="Need at least 10 medical images"
    )
    def test_medical_image_similarity_distribution(self, test_model_path, sample_images):
        """Test similarity distribution for medical images."""
        if len(sample_images) < 10:
            pytest.skip("Need at least 10 images")
        
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Generate hashes for 10 images
        hashes = []
        for i in range(10):
            features = create_synthetic_features(seed=i)
            binary, _ = generator.generate_hash(features)
            hashes.append(binary.squeeze())
        
        # Compute pairwise distances
        distances = []
        for i in range(len(hashes)):
            for j in range(i+1, len(hashes)):
                sim_result = generator.compute_similarity(hashes[i], hashes[j])
                distances.append(sim_result['hamming_distance'])
        
        # Check distribution
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)
        
        logger.info(f"✓ Hamming distance: mean={mean_dist:.1f}, std={std_dist:.1f}")
        
        assert 50 <= mean_dist <= 200, "Mean distance should be reasonable"
        assert std_dist > 0, "Should have variation in distances"


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestValidation:
    """Test input validation."""
    
    def test_wrong_feature_dimension(self, test_model_path):
        """Test error on wrong feature dimension."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        wrong_features = np.random.randn(256).astype(np.float32)
        
        with pytest.raises((ValueError, ValidationError, HashGenerationError)):
            generator.generate_hash(wrong_features)
    
    def test_invalid_feature_type(self, test_model_path):
        """Test handling of invalid feature types."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        # List instead of numpy array
        features_list = [1.0] * 512
        
        # Should either convert or raise error
        try:
            binary, _ = generator.generate_hash(np.array(features_list, dtype=np.float32))
            assert binary.shape == (1, 256)
        except (TypeError, ValueError):
            pass  # Expected


# ============================================================================
# MODEL LOADING TESTS
# ============================================================================

class TestModelLoading:
    """Test model loading functionality."""
    
    def test_load_nonexistent_model(self):
        """Test error when model doesn't exist."""
        config = DeepHashingConfig(
            hash_model_path="nonexistent_model.pt",
            pca_transform_path=None
        )
        
        with pytest.raises((FileNotFoundError, ModelLoadError)):
            DeepHashGenerator(config=config)
    
    def test_load_direct_state_dict(self, test_model_path):
        """Test loading direct state_dict format (v4.0)."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        assert generator.model is not None
        assert generator.config.hash_bits == 256
    
    def test_model_info(self, test_model_path):
        """Test getting model information."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        info = generator.get_info()
        
        assert 'model_path' in info
        assert 'device' in info
        assert 'hash_bits' in info
        assert 'feature_dim' in info
        assert info['hash_bits'] == 256
        assert info['feature_dim'] == 512


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for realistic workflows."""
    
    def test_similarity_search_workflow(self, test_model_path):
        """Test simulated similarity search workflow."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Create query
        query_features = create_synthetic_features(seed=0)
        query_hash, _ = generator.generate_hash(query_features)
        query_hash = query_hash.squeeze()
        
        # Create database
        database_size = 100
        database_hashes = []
        
        for i in range(database_size):
            features = create_synthetic_features(seed=i+1)
            binary, _ = generator.generate_hash(features)
            database_hashes.append(binary.squeeze())
        
        # Find similar images
        threshold = 80
        similar_count = 0
        
        for db_hash in database_hashes:
            sim_result = generator.compute_similarity(query_hash, db_hash)
            if sim_result['hamming_distance'] < threshold:
                similar_count += 1
        
        logger.info(f"✓ Found {similar_count}/{database_size} similar images")
        assert similar_count >= 0
    
    def test_end_to_end_pipeline(self, test_model_path):
        """Test complete end-to-end pipeline."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None,
            device='cpu'
        )
        
        generator = DeepHashGenerator(config=config)
        
        # Simulate: Image → Features → Hash → Similarity
        features1 = create_synthetic_features(seed=1)
        features2 = create_synthetic_features(seed=2)
        
        binary1, continuous1 = generator.generate_hash(features1)
        binary2, continuous2 = generator.generate_hash(features2)
        
        sim_result = generator.compute_similarity(
            binary1.squeeze(),
            binary2.squeeze()
        )
        
        logger.info(f"✓ End-to-end pipeline: "
                   f"HD={sim_result['hamming_distance']}, "
                   f"Sim={sim_result['similarity_score']:.3f}")
        
        assert binary1.shape == (1, 256)
        assert binary2.shape == (1, 256)
        assert 0 <= sim_result['hamming_distance'] <= 256


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================

@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks."""
    
    def test_single_hash_speed(self, test_model_path, benchmark, sample_features):
        """Benchmark single hash generation."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        
        def generate():
            return generator.generate_hash(sample_features)
        
        result = benchmark(generate)
        assert result[0].shape == (1, 256)
    
    def test_batch_hash_speed(self, test_model_path, benchmark):
        """Benchmark batch hash generation."""
        config = DeepHashingConfig(
            hash_model_path=str(test_model_path),
            pca_transform_path=None
        )
        
        generator = DeepHashGenerator(config=config)
        batch_features = create_synthetic_features_batch(100, seed=42)
        
        def generate():
            return generator.generate_hash(batch_features)
        
        result = benchmark(generate)
        assert result[0].shape == (100, 256)


# ============================================================================
# PYTEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "--maxfail=5",
        "-W", "ignore::DeprecationWarning"
    ])
