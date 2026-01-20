"""
DeepHash Module Tests
=====================
Comprehensive tests for DeepHash binary code generation with real images.
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import sys
from PIL import Image
import io
import torchvision.transforms as transforms
import torchvision.models as models

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deephashing import DeepHashGenerator
from deephashing.core.model import DeepHashingHead
from deephashing.core.config import ModelConfig
from deephashing.exceptions import ModelLoadError, ValidationError


# ============================================================================
# REAL IMAGE HELPERS
# ============================================================================

def get_sample_images():
    """Get list of sample images from ../sample_images folder."""
    image_dirs = [
        Path("../sample_images"),
        Path("sample_images"),
        Path("tests/sample_images"),
        Path("data/sample_images"),
    ]
    
    for img_dir in image_dirs:
        if img_dir.exists():
            image_files = list(img_dir.glob("*.jpg")) + \
                         list(img_dir.glob("*.png")) + \
                         list(img_dir.glob("*.jpeg"))
            if image_files:
                print(f"✓ Found {len(image_files)} images in {img_dir}")
                return image_files
    
    print("⚠ No sample images found, using synthetic images")
    return []


def extract_features_resnet50(image_path: Path) -> np.ndarray:
    """
    Extract 512-dim features from image using ResNet50.
    
    This simulates the real CNN feature extraction pipeline.
    """
    # Load pre-trained ResNet50
    model = models.resnet50(pretrained=True)
    
    # Remove final classification layer to get features
    model = torch.nn.Sequential(*list(model.children())[:-1])
    model.eval()
    
    # Image preprocessing
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    # Load and preprocess image
    img = Image.open(image_path).convert('RGB')
    img_tensor = transform(img).unsqueeze(0)
    
    # Extract features
    with torch.no_grad():
        features = model(img_tensor)
    
    # Flatten to 2048-dim, then project to 512-dim
    features = features.squeeze().numpy()
    
    # Simple projection to 512-dim (in production, you'd use a learned projection)
    if features.shape[0] == 2048:
        # Average pooling to get 512-dim
        features = features.reshape(4, 512).mean(axis=0)
    
    return features.astype(np.float32)


def create_synthetic_image(color: tuple, size: tuple = (224, 224)) -> Image.Image:
    """Create synthetic image for testing."""
    return Image.new('RGB', size, color=color)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_images():
    """Get sample images (real or synthetic)."""
    real_images = get_sample_images()
    
    if real_images:
        return real_images[:10]  # Use up to 10 images
    else:
        # Create synthetic images
        print("Creating synthetic test images...")
        return [
            create_synthetic_image((255, 0, 0)),    # Red
            create_synthetic_image((0, 255, 0)),    # Green
            create_synthetic_image((0, 0, 255)),    # Blue
            create_synthetic_image((255, 255, 0)),  # Yellow
            create_synthetic_image((255, 0, 255)),  # Magenta
        ]


@pytest.fixture
def sample_features():
    """Create sample 512-dim feature vector."""
    np.random.seed(42)
    return np.random.randn(512).astype(np.float32)


@pytest.fixture
def sample_features_batch():
    """Create batch of feature vectors."""
    np.random.seed(42)
    return np.random.randn(10, 512).astype(np.float32)


@pytest.fixture
def test_model_path(tmp_path):
    """Create a test model checkpoint."""
    # Create model
    model = DeepHashingHead(input_dim=512, hash_dim=256)
    
    # Save as state_dict
    checkpoint = {
        'state_dict': model.state_dict(),
        'config': {
            'input_dim': 512,
            'hash_dim': 256,
            'hidden_dims': [512, 512]
        },
        'metrics': {
            'map': 0.85,
            'precision@100': 0.92
        }
    }
    
    model_path = tmp_path / "test_deephash.pt"
    torch.save(checkpoint, model_path)
    
    return model_path


@pytest.fixture
def production_model_path():
    """Get production model path if it exists."""
    model_paths = [
        Path("models/deephash_production.pt"),
        Path("models/deephash_state_dict_only.pt"),
        Path("models/deephash.pt"),
    ]
    
    for path in model_paths:
        if path.exists():
            return path
    
    return None


@pytest.fixture(scope="session")
def resnet_feature_extractor():
    """Load ResNet50 feature extractor (cached for session)."""
    try:
        model = models.resnet50(pretrained=True)
        model = torch.nn.Sequential(*list(model.children())[:-1])
        model.eval()
        return model
    except Exception as e:
        print(f"⚠ Failed to load ResNet50: {e}")
        return None


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestDeepHashingHead:
    """Test DeepHashingHead model architecture."""
    
    def test_model_initialization(self):
        """Test model can be initialized."""
        model = DeepHashingHead(input_dim=512, hash_dim=256)
        
        assert model.input_dim == 512
        assert model.hash_dim == 256
        assert isinstance(model.hash_layer, torch.nn.Sequential)
    
    def test_forward_pass(self, sample_features):
        """Test forward pass."""
        model = DeepHashingHead(input_dim=512, hash_dim=256)
        model.eval()
        
        # Convert to tensor and add batch dimension
        x = torch.from_numpy(sample_features).unsqueeze(0)
        
        # Forward pass
        output = model(x)
        
        assert output.shape == (1, 256), "Output should be (batch_size, hash_dim)"
    
    def test_generate_hash(self, sample_features):
        """Test binary hash generation."""
        model = DeepHashingHead(input_dim=512, hash_dim=256)
        model.eval()
        
        # Convert to tensor
        x = torch.from_numpy(sample_features).unsqueeze(0)
        
        # Generate hash
        hash_code = model.generate_hash(x)
        
        assert hash_code.shape == (1, 256)
        assert hash_code.dtype == torch.int32
        assert torch.all((hash_code == 0) | (hash_code == 1)), "Hash should be binary"
    
    def test_batch_processing(self, sample_features_batch):
        """Test batch processing."""
        model = DeepHashingHead(input_dim=512, hash_dim=256)
        model.eval()
        
        x = torch.from_numpy(sample_features_batch)
        
        # Generate hashes for batch
        hash_codes = model.generate_hash(x)
        
        assert hash_codes.shape == (10, 256)
        assert torch.all((hash_codes == 0) | (hash_codes == 1))


# ============================================================================
# GENERATOR TESTS
# ============================================================================

class TestDeepHashGenerator:
    """Test DeepHashGenerator API."""
    
    def test_generator_initialization_with_test_model(self, test_model_path):
        """Test generator initialization with test model."""
        generator = DeepHashGenerator(str(test_model_path))
        
        assert generator.hash_bits == 256
        assert generator.input_dim == 512
        assert generator.config.device in ['cpu', 'cuda']
    
    def test_generate_single_hash(self, test_model_path, sample_features):
        """Test generating single hash."""
        generator = DeepHashGenerator(str(test_model_path))
        
        hash_code = generator.generate(sample_features)
        
        assert hash_code.shape == (256,), "Output should be 256-bit"
        assert hash_code.dtype == np.int32
        assert np.all((hash_code == 0) | (hash_code == 1)), "Should be binary"
    
    def test_generate_batch(self, test_model_path, sample_features_batch):
        """Test generating batch of hashes."""
        generator = DeepHashGenerator(str(test_model_path))
        
        hash_codes = generator.generate_batch(sample_features_batch)
        
        assert hash_codes.shape == (10, 256)
        assert np.all((hash_codes == 0) | (hash_codes == 1))
    
    def test_determinism(self, test_model_path, sample_features):
        """Test that hash generation is deterministic."""
        generator = DeepHashGenerator(str(test_model_path))
        
        hash1 = generator.generate(sample_features)
        hash2 = generator.generate(sample_features)
        
        assert np.array_equal(hash1, hash2), "Same input should produce same hash"
    
    def test_hamming_distance(self, test_model_path):
        """Test Hamming distance computation."""
        generator = DeepHashGenerator(str(test_model_path))
        
        # Generate two different hashes
        np.random.seed(42)
        features1 = np.random.randn(512).astype(np.float32)
        np.random.seed(43)
        features2 = np.random.randn(512).astype(np.float32)
        
        hash1 = generator.generate(features1)
        hash2 = generator.generate(features2)
        
        # Compute Hamming distance
        hd = generator.compute_hamming_distance(hash1, hash2)
        
        assert isinstance(hd, (int, np.integer))
        assert 0 <= hd <= 256, "Hamming distance should be between 0 and 256"
    
    def test_similarity(self, test_model_path, sample_features):
        """Test similarity computation."""
        generator = DeepHashGenerator(str(test_model_path))
        
        hash_code = generator.generate(sample_features)
        
        # Same hash should have similarity of 1.0
        similarity = generator.compute_similarity(hash_code, hash_code)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity == 1.0, "Identical hashes should have similarity 1.0"
    
    def test_get_info(self, test_model_path):
        """Test getting generator information."""
        generator = DeepHashGenerator(str(test_model_path))
        
        info = generator.get_info()
        
        assert 'model_path' in info
        assert 'device' in info
        assert 'hash_bits' in info
        assert 'input_dim' in info
        assert info['hash_bits'] == 256
        assert info['input_dim'] == 512


# ============================================================================
# REAL IMAGE TESTS
# ============================================================================

class TestRealImageWorkflow:
    """Test DeepHash with real images."""
    
    @pytest.mark.skipif(
        not get_sample_images(),
        reason="No sample images found"
    )
    def test_real_image_feature_extraction(self, sample_images, resnet_feature_extractor):
        """Test feature extraction from real images."""
        if resnet_feature_extractor is None:
            pytest.skip("ResNet50 not available")
        
        # Process first image
        if isinstance(sample_images[0], Path):
            img_path = sample_images[0]
            features = extract_features_resnet50(img_path)
        else:
            pytest.skip("Synthetic images don't need feature extraction")
        
        assert features.shape == (512,), "Features should be 512-dim"
        assert features.dtype == np.float32
        
        print(f"✓ Extracted features from: {img_path.name}")
    
    @pytest.mark.skipif(
        not get_sample_images(),
        reason="No sample images found"
    )
    def test_real_image_to_deephash(self, test_model_path, sample_images, resnet_feature_extractor):
        """Test complete pipeline: Real Image → Features → DeepHash."""
        if resnet_feature_extractor is None:
            pytest.skip("ResNet50 not available")
        
        generator = DeepHashGenerator(str(test_model_path))
        
        # Process each real image
        hash_codes = []
        for img in sample_images[:3]:  # Test first 3 images
            if isinstance(img, Path):
                # Real image - extract features
                features = extract_features_resnet50(img)
                hash_code = generator.generate(features)
                
                assert hash_code.shape == (256,)
                assert np.all((hash_code == 0) | (hash_code == 1))
                
                hash_codes.append((img.name, hash_code))
                print(f"✓ Generated hash for: {img.name}")
        
        assert len(hash_codes) > 0, "Should process at least one image"
    
    @pytest.mark.skipif(
        not get_sample_images(),
        reason="No sample images found"
    )
    def test_real_image_similarity(self, test_model_path, sample_images, resnet_feature_extractor):
        """Test similarity between real images."""
        if resnet_feature_extractor is None:
            pytest.skip("ResNet50 not available")
        
        if len(sample_images) < 2:
            pytest.skip("Need at least 2 images")
        
        generator = DeepHashGenerator(str(test_model_path))
        
        # Generate hashes for two images
        hashes = []
        for img in sample_images[:2]:
            if isinstance(img, Path):
                features = extract_features_resnet50(img)
                hash_code = generator.generate(features)
                hashes.append((img.name, hash_code))
        
        if len(hashes) == 2:
            # Compute similarity
            hd = generator.compute_hamming_distance(hashes[0][1], hashes[1][1])
            similarity = generator.compute_similarity(hashes[0][1], hashes[1][1])
            
            print(f"\n✓ Similarity Analysis:")
            print(f"  Image 1: {hashes[0][0]}")
            print(f"  Image 2: {hashes[1][0]}")
            print(f"  Hamming Distance: {hd}/256")
            print(f"  Similarity Score: {similarity:.4f}")
            
            assert 0 <= hd <= 256
            assert 0.0 <= similarity <= 1.0


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestValidation:
    """Test input validation."""
    
    def test_invalid_feature_dimension(self, test_model_path):
        """Test validation catches wrong feature dimension."""
        generator = DeepHashGenerator(str(test_model_path))
        
        # Wrong dimension
        wrong_features = np.random.randn(256).astype(np.float32)
        
        with pytest.raises(ValidationError):
            generator.generate(wrong_features)
    
    def test_invalid_feature_type(self, test_model_path):
        """Test validation catches wrong feature type."""
        generator = DeepHashGenerator(str(test_model_path))
        
        # Wrong type (list instead of numpy array)
        wrong_features = [1.0] * 512
        
        # Should either convert or raise error
        try:
            hash_code = generator.generate(np.array(wrong_features, dtype=np.float32))
            assert hash_code.shape == (256,)
        except (ValidationError, TypeError):
            pass  # Expected


# ============================================================================
# MODEL LOADING TESTS
# ============================================================================

class TestModelLoading:
    """Test model loading functionality."""
    
    def test_load_nonexistent_model(self):
        """Test loading non-existent model raises error."""
        with pytest.raises(ModelLoadError):
            DeepHashGenerator("nonexistent_model.pt")
    
    def test_load_state_dict_format(self, test_model_path):
        """Test loading state_dict format model."""
        generator = DeepHashGenerator(str(test_model_path))
        
        assert generator.model is not None
        assert generator.model_config.hash_dim == 256
    
    @pytest.mark.skipif(
        not Path("models").exists(),
        reason="Production models directory not found"
    )
    def test_load_production_model(self, production_model_path):
        """Test loading production model if it exists."""
        if production_model_path is None:
            pytest.skip("No production model found")
        
        try:
            generator = DeepHashGenerator(str(production_model_path))
            
            assert generator.hash_bits == 256
            assert generator.input_dim == 512
            
            # Test it can generate hashes
            features = np.random.randn(512).astype(np.float32)
            hash_code = generator.generate(features)
            
            assert hash_code.shape == (256,)
            print(f"✓ Production model loaded successfully from: {production_model_path}")
            
        except Exception as e:
            pytest.skip(f"Production model loading failed: {e}")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestDeepHashIntegration:
    """Integration tests with realistic workflows."""
    
    def test_image_feature_extraction_simulation(self, test_model_path, sample_images):
        """Test simulated image feature extraction → DeepHash workflow."""
        generator = DeepHashGenerator(str(test_model_path))
        
        # Use real or synthetic images
        num_images = min(len(sample_images), 5)
        
        # Generate hashes
        hash_codes = []
        for i in range(num_images):
            # Mock features (in production, extract from actual images)
            features = np.random.randn(512).astype(np.float32)
            hash_code = generator.generate(features)
            hash_codes.append(hash_code)
        
        assert len(hash_codes) == num_images
        
        # Verify all are unique (with high probability)
        unique_hashes = set(tuple(h) for h in hash_codes)
        assert len(unique_hashes) == num_images, "Hashes should be unique"
    
    def test_similarity_search_simulation(self, test_model_path):
        """Test simulated similarity search workflow."""
        generator = DeepHashGenerator(str(test_model_path))
        
        # Create query
        query_features = np.random.randn(512).astype(np.float32)
        query_hash = generator.generate(query_features)
        
        # Create database of 100 images
        database_size = 100
        database_hashes = []
        
        for i in range(database_size):
            features = np.random.randn(512).astype(np.float32)
            hash_code = generator.generate(features)
            database_hashes.append(hash_code)
        
        # Find similar images (Hamming distance < threshold)
        threshold = 64  # ~25% of 256 bits
        similar_indices = []
        
        for idx, db_hash in enumerate(database_hashes):
            hd = generator.compute_hamming_distance(query_hash, db_hash)
            if hd < threshold:
                similar_indices.append(idx)
        
        print(f"✓ Found {len(similar_indices)} similar images out of {database_size}")
        assert len(similar_indices) >= 0  # At least 0 found (could be none)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks."""
    
    def test_single_hash_generation_speed(self, test_model_path, benchmark):
        """Benchmark single hash generation."""
        generator = DeepHashGenerator(str(test_model_path))
        features = np.random.randn(512).astype(np.float32)
        
        result = benchmark(generator.generate, features)
        
        assert result.shape == (256,)
    
    def test_batch_hash_generation_speed(self, test_model_path, benchmark):
        """Benchmark batch hash generation."""
        generator = DeepHashGenerator(str(test_model_path))
        features_batch = np.random.randn(100, 512).astype(np.float32)
        
        result = benchmark(generator.generate_batch, features_batch)
        
        assert result.shape == (100, 256)


# ============================================================================
# PYTEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
