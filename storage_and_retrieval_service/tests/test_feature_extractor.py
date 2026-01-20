"""
Complete Feature Extractor Test Suite
======================================

Single file to test ConvNeXtFeatureExtractor with real images.

Run with:
    python tests/test_feature_extractor_standalone.py

Or with pytest:
    pytest tests/test_feature_extractor_standalone.py -v
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import torch
from PIL import Image
import logging

from feature_extractor.extractor import ConvNeXtFeatureExtractor
from feature_extractor.exceptions import FeatureExtractionError, ModelLoadError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureExtractorTester:
    """Comprehensive tester for feature extractor."""
    
    def __init__(self):
        self.model_path = Path("models/convnext_state_dict_only.pt")
        self.sample_images_dir = Path("sample_images")
        self.extractor = None
        self.image_paths = []
        
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
    def print_header(self, title):
        """Print section header."""
        print("\n" + "="*70)
        print(f"{title}")
        print("="*70)
    
    def print_test(self, test_name):
        """Print test name."""
        print(f"\n{'Test:':<50} {test_name}")
        print("-" * 70)
    
    def print_result(self, passed, message=""):
        """Print test result."""
        if passed:
            self.passed_tests += 1
            status = "✅ PASSED"
        else:
            self.failed_tests += 1
            status = "❌ FAILED"
        
        print(f"{'Status:':<50} {status}")
        if message:
            print(f"{'Info:':<50} {message}")
    
    def setup(self):
        """Setup test environment."""
        self.print_header("SETUP: Feature Extractor Test Suite")
        
        # Check model exists
        print(f"\nChecking model path: {self.model_path}")
        if not self.model_path.exists():
            print(f"❌ Model not found: {self.model_path}")
            print("Please place your model at models/convnext_best.pt")
            return False
        print(f"✅ Model found: {self.model_path}")
        
        # Check sample images directory
        print(f"\nChecking sample images: {self.sample_images_dir}")
        if not self.sample_images_dir.exists():
            print(f"❌ Sample images directory not found")
            return False
        
        # Get image paths
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        for ext in extensions:
            self.image_paths.extend(list(self.sample_images_dir.glob(ext)))
            self.image_paths.extend(list(self.sample_images_dir.glob(ext.upper())))
        
        if not self.image_paths:
            print(f"❌ No images found in {self.sample_images_dir}")
            return False
        
        self.image_paths = sorted(self.image_paths)[:10]  # Limit to 10
        print(f"✅ Found {len(self.image_paths)} sample images")
        
        # Load extractor
        print(f"\nLoading feature extractor...")
        try:
            self.extractor = ConvNeXtFeatureExtractor(
                model_path=self.model_path,
                device=None,  # Auto-detect
                batch_size=4
            )
            print(f"✅ Extractor loaded successfully")
            print(f"   - Device: {self.extractor.config.device}")
            print(f"   - Feature dimension: {self.extractor.feature_dim}")
            print(f"   - Batch size: {self.extractor.config.batch_size}")
            return True
        except Exception as e:
            print(f"❌ Failed to load extractor: {e}")
            return False
    
    # ========================================================================
    # Model Initialization Tests
    # ========================================================================
    
    def test_model_loaded(self):
        """Test 1: Model is loaded successfully."""
        self.print_test("Model Initialization")
        
        passed = self.extractor.model is not None
        self.print_result(passed, f"Model: {type(self.extractor.model).__name__}")
        return passed
    
    def test_feature_dimension(self):
        """Test 2: Feature dimension is 512."""
        self.print_test("Feature Dimension Check")
        
        passed = self.extractor.feature_dim == 512
        self.print_result(passed, f"Dimension: {self.extractor.feature_dim}")
        return passed
    
    def test_eval_mode(self):
        """Test 3: Model is in evaluation mode."""
        self.print_test("Model Evaluation Mode")
        
        passed = not self.extractor.model.training
        self.print_result(passed, f"Training mode: {self.extractor.model.training}")
        return passed
    
    # ========================================================================
    # Single Image Extraction Tests
    # ========================================================================
    
    def test_extract_from_path_string(self):
        """Test 4: Extract features from image path (string)."""
        self.print_test("Single Image Extraction (Path String)")
        
        try:
            image_path = str(self.image_paths[0])
            features = self.extractor.extract(image_path)
            
            passed = (
                isinstance(features, np.ndarray) and
                features.shape == (512,) and
                features.dtype == np.float32
            )
            
            self.print_result(
                passed,
                f"Shape: {features.shape}, Dtype: {features.dtype}"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_path_object(self):
        """Test 5: Extract features from Path object."""
        self.print_test("Single Image Extraction (Path Object)")
        
        try:
            image_path = self.image_paths[0]
            features = self.extractor.extract(image_path)
            
            passed = features.shape == (512,)
            self.print_result(passed, f"Image: {image_path.name}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_pil_image(self):
        """Test 6: Extract features from PIL Image."""
        self.print_test("Single Image Extraction (PIL Image)")
        
        try:
            pil_image = Image.open(self.image_paths[0])
            features = self.extractor.extract(pil_image)
            
            passed = features.shape == (512,)
            self.print_result(passed, f"PIL mode: {pil_image.mode}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_numpy_array(self):
        """Test 7: Extract features from numpy array."""
        self.print_test("Single Image Extraction (NumPy Array)")
        
        try:
            pil_image = Image.open(self.image_paths[0])
            np_image = np.array(pil_image)
            features = self.extractor.extract(np_image)
            
            passed = features.shape == (512,)
            self.print_result(passed, f"Array shape: {np_image.shape}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Feature Normalization Tests
    # ========================================================================
    
    def test_feature_normalization(self):
        """Test 8: Features are L2 normalized."""
        self.print_test("Feature L2 Normalization")
        
        try:
            features = self.extractor.extract(self.image_paths[0], normalize=True)
            l2_norm = np.linalg.norm(features)
            
            passed = np.isclose(l2_norm, 1.0, atol=1e-5)
            self.print_result(passed, f"L2 norm: {l2_norm:.6f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_without_normalization(self):
        """Test 9: Features without normalization."""
        self.print_test("Feature Without Normalization")
        
        try:
            features = self.extractor.extract(self.image_paths[0], normalize=False)
            l2_norm = np.linalg.norm(features)
            
            passed = not np.isclose(l2_norm, 1.0, atol=1e-5)
            self.print_result(passed, f"L2 norm: {l2_norm:.6f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Batch Extraction Tests
    # ========================================================================
    
    def test_batch_extraction(self):
        """Test 10: Extract features from batch of images."""
        self.print_test("Batch Feature Extraction")
        
        try:
            batch_size = min(5, len(self.image_paths))
            features = self.extractor.extract_batch(self.image_paths[:batch_size])
            
            passed = (
                features.shape[0] == batch_size and
                features.shape[1] == 512
            )
            
            self.print_result(passed, f"Batch shape: {features.shape}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_batch_normalization(self):
        """Test 11: Batch features are normalized."""
        self.print_test("Batch Feature Normalization")
        
        try:
            features = self.extractor.extract_batch(
                self.image_paths[:3],
                normalize=True
            )
            
            # Check each feature is normalized
            norms = [np.linalg.norm(features[i]) for i in range(features.shape[0])]
            passed = all(np.isclose(norm, 1.0, atol=1e-5) for norm in norms)
            
            self.print_result(
                passed,
                f"L2 norms: {[f'{n:.6f}' for n in norms]}"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Consistency Tests
    # ========================================================================
    
    def test_same_image_consistency(self):
        """Test 12: Same image produces same features."""
        self.print_test("Feature Consistency (Same Image)")
        
        try:
            features1 = self.extractor.extract(self.image_paths[0])
            features2 = self.extractor.extract(self.image_paths[0])
            
            passed = np.allclose(features1, features2, atol=1e-5)
            diff = np.abs(features1 - features2).max()
            
            self.print_result(passed, f"Max difference: {diff:.10f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_different_images_different_features(self):
        """Test 13: Different images produce different features."""
        self.print_test("Feature Uniqueness (Different Images)")
        
        try:
            if len(self.image_paths) < 2:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Need at least 2 images")
                return True
            
            features1 = self.extractor.extract(self.image_paths[0])
            features2 = self.extractor.extract(self.image_paths[1])
            
            passed = not np.allclose(features1, features2)
            similarity = np.dot(features1, features2)
            
            self.print_result(passed, f"Cosine similarity: {similarity:.6f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_single_vs_batch_consistency(self):
        """Test 14: Single and batch extraction match."""
        self.print_test("Single vs Batch Consistency")
        
        try:
            single_features = self.extractor.extract(self.image_paths[0])
            batch_features = self.extractor.extract_batch([self.image_paths[0]])
            
            passed = np.allclose(single_features, batch_features[0], atol=1e-5)
            diff = np.abs(single_features - batch_features[0]).max()
            
            self.print_result(passed, f"Max difference: {diff:.10f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Feature Properties Tests
    # ========================================================================
    
    def test_feature_range(self):
        """Test 15: Feature values are in valid range."""
        self.print_test("Feature Value Range")
        
        try:
            features = self.extractor.extract(self.image_paths[0])
            
            passed = np.all(features >= -1.0) and np.all(features <= 1.0)
            
            self.print_result(
                passed,
                f"Min: {features.min():.6f}, Max: {features.max():.6f}"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_feature_statistics(self):
        """Test 16: Feature statistics."""
        self.print_test("Feature Statistics")
        
        try:
            features = self.extractor.extract(self.image_paths[0])
            
            stats = {
                'mean': features.mean(),
                'std': features.std(),
                'min': features.min(),
                'max': features.max(),
                'non_zero': np.count_nonzero(features)
            }
            
            passed = (
                -1.0 <= stats['min'] <= 1.0 and
                -1.0 <= stats['max'] <= 1.0 and
                stats['non_zero'] > 0
            )
            
            info = f"Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}, Non-zero: {stats['non_zero']}/512"
            self.print_result(passed, info)
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Integration Tests
    # ========================================================================
    
    def test_similarity_matrix(self):
        """Test 17: Compute similarity matrix."""
        self.print_test("Similarity Matrix Computation")
        
        try:
            num_images = min(3, len(self.image_paths))
            features = self.extractor.extract_batch(self.image_paths[:num_images])
            
            similarity = np.dot(features, features.T)
            
            # Diagonal should be 1 (self-similarity)
            diagonal = np.diag(similarity)
            passed = np.allclose(diagonal, 1.0, atol=1e-5)
            
            print(f"\nSimilarity Matrix:")
            for i in range(num_images):
                print(f"  Image {i}: ", end="")
                for j in range(num_images):
                    print(f"{similarity[i, j]:.3f} ", end="")
                print()
            
            self.print_result(passed, f"Diagonal: {diagonal}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extractor_info(self):
        """Test 18: Get extractor information."""
        self.print_test("Extractor Information")
        
        try:
            info = self.extractor.get_info()
            
            required_keys = ['model_path', 'device', 'feature_dim', 'batch_size', 'model_type']
            passed = all(key in info for key in required_keys)
            
            print(f"\nExtractor Info:")
            for key, value in info.items():
                print(f"  {key}: {value}")
            
            self.print_result(passed, f"All keys present: {passed}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Main Test Runner
    # ========================================================================
    
    def run_all_tests(self):
        """Run all tests."""
        self.print_header("RUNNING ALL TESTS")
        
        if not self.setup():
            print("\n❌ Setup failed. Cannot run tests.")
            return False
        
        # Run all test methods
        test_methods = [
            self.test_model_loaded,
            self.test_feature_dimension,
            self.test_eval_mode,
            self.test_extract_from_path_string,
            self.test_extract_from_path_object,
            self.test_extract_from_pil_image,
            self.test_extract_from_numpy_array,
            self.test_feature_normalization,
            self.test_without_normalization,
            self.test_batch_extraction,
            self.test_batch_normalization,
            self.test_same_image_consistency,
            self.test_different_images_different_features,
            self.test_single_vs_batch_consistency,
            self.test_feature_range,
            self.test_feature_statistics,
            self.test_similarity_matrix,
            self.test_extractor_info,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.failed_tests += 1
                print(f"\n❌ Test crashed: {e}")
        
        # Print summary
        self.print_summary()
        
        return self.failed_tests == 0
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("TEST SUMMARY")
        
        total = self.passed_tests + self.failed_tests + self.skipped_tests
        
        print(f"\n{'Total Tests:':<30} {total}")
        print(f"{'✅ Passed:':<30} {self.passed_tests}")
        print(f"{'❌ Failed:':<30} {self.failed_tests}")
        print(f"{'⚠️  Skipped:':<30} {self.skipped_tests}")
        
        if self.failed_tests == 0:
            print(f"\n{'='*70}")
            print(f"{'🎉 ALL TESTS PASSED! 🎉':^70}")
            print(f"{'='*70}")
        else:
            print(f"\n{'='*70}")
            print(f"{'⚠️  SOME TESTS FAILED':^70}")
            print(f"{'='*70}")


def main():
    """Main entry point."""
    tester = FeatureExtractorTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
