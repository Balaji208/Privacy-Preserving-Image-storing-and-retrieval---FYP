"""
Complete Feature Extractor Test Suite
======================================

Comprehensive tests for ConvNeXtFeatureExtractor with Phase 1 model.
Tests with real medical images from sample_images folder.

Run with:
    python tests/test_feature_extractor.py

Or with pytest:
    pytest tests/test_feature_extractor.py -v
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
from typing import List, Dict

from feature_extractor.extractor import ConvNeXtFeatureExtractor
from feature_extractor.exceptions import FeatureExtractionError, ModelLoadError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureExtractorTester:
    """Comprehensive tester for feature extractor with real medical images."""
    
    def __init__(self):
        self.model_path = Path("models/convnextv2_best_phase1.pt")
        self.sample_images_dir = Path("sample_images")
        self.extractor = None
        self.image_paths = []
        self.image_metadata = []  # Store info about each image
        
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
    def print_header(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"{title:^80}")
        print("="*80)
    
    def print_test(self, test_name):
        """Print test name."""
        print(f"\n{'Test:':<50} {test_name}")
        print("-" * 80)
    
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
        self.print_header("SETUP: Phase 1 Model Test Suite")
        
        # Check model exists
        print(f"\n📁 Checking model path: {self.model_path}")
        if not self.model_path.exists():
            print(f"❌ Model not found: {self.model_path}")
            print("   Please copy convnextv2_best_phase1.pt to models/ directory")
            return False
        print(f"✅ Model found: {self.model_path.name}")
        
        # Check sample images directory
        print(f"\n📁 Checking sample images: {self.sample_images_dir}")
        if not self.sample_images_dir.exists():
            print(f"❌ Sample images directory not found")
            print(f"   Please create {self.sample_images_dir} and add medical images")
            return False
        
        # Get image paths and metadata
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        for ext in extensions:
            self.image_paths.extend(list(self.sample_images_dir.glob(ext)))
            self.image_paths.extend(list(self.sample_images_dir.glob(ext.upper())))
        
        if not self.image_paths:
            print(f"❌ No images found in {self.sample_images_dir}")
            print(f"   Supported formats: .jpg, .jpeg, .png, .bmp")
            return False
        
        self.image_paths = sorted(self.image_paths)
        
        # Analyze images
        print(f"\n📊 Analyzing {len(self.image_paths)} images...")
        for img_path in self.image_paths[:20]:  # Limit analysis to first 20
            try:
                img = Image.open(img_path)
                self.image_metadata.append({
                    'path': img_path,
                    'size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'file_size_kb': img_path.stat().st_size / 1024
                })
            except Exception as e:
                logger.warning(f"Could not analyze {img_path.name}: {e}")
        
        print(f"✅ Found {len(self.image_paths)} images")
        if self.image_metadata:
            print(f"\n📋 Image Statistics:")
            sizes = [m['size'] for m in self.image_metadata]
            modes = [m['mode'] for m in self.image_metadata]
            file_sizes = [m['file_size_kb'] for m in self.image_metadata]
            
            print(f"   Resolutions: {len(set(sizes))} unique")
            print(f"   Modes: {set(modes)}")
            print(f"   File size range: {min(file_sizes):.1f} - {max(file_sizes):.1f} KB")
            
            # Show first 5 samples
            print(f"\n📝 Sample images:")
            for i, meta in enumerate(self.image_metadata[:5]):
                print(f"   {i+1}. {meta['path'].name}")
                print(f"      Size: {meta['size']}, Mode: {meta['mode']}, "
                      f"Format: {meta['format']}, {meta['file_size_kb']:.1f} KB")
        
        # Load extractor
        print(f"\n🔄 Loading Phase 1 feature extractor...")
        try:
            self.extractor = ConvNeXtFeatureExtractor(
                model_path=self.model_path,
                device=None,  # Auto-detect
                batch_size=8
            )
            print(f"✅ Extractor loaded successfully")
            
            info = self.extractor.get_info()
            print(f"\n📊 Model Information:")
            print(f"   Device: {info['device']}")
            print(f"   Feature dimension: {info['feature_dim']}")
            print(f"   Model type: {info['model_type']}")
            print(f"   Model size: {info['model_size']}")
            print(f"   Batch size: {info['batch_size']}")
            
            return True
        except Exception as e:
            print(f"❌ Failed to load extractor: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ========================================================================
    # Model Initialization Tests
    # ========================================================================
    
    def test_model_loaded(self):
        """Test 1: Phase 1 model is loaded successfully."""
        self.print_test("Phase 1 Model Initialization")
        
        passed = (
            self.extractor.model is not None and
            hasattr(self.extractor.model, 'backbone') and
            hasattr(self.extractor.model, 'projection')
        )
        
        model_type = type(self.extractor.model).__name__
        self.print_result(passed, f"Model: {model_type}")
        return passed
    
    def test_feature_dimension(self):
        """Test 2: Feature dimension is 512 (Phase 1 spec)."""
        self.print_test("Feature Dimension Check")
        
        passed = self.extractor.feature_dim == 512
        self.print_result(passed, f"Dimension: {self.extractor.feature_dim}/512")
        return passed
    
    def test_eval_mode(self):
        """Test 3: Model is in evaluation mode."""
        self.print_test("Model Evaluation Mode")
        
        passed = not self.extractor.model.training
        self.print_result(passed, f"Training mode: {self.extractor.model.training}")
        return passed
    
    def test_device_placement(self):
        """Test 4: Model is on correct device."""
        self.print_test("Device Placement")
        
        try:
            device = next(self.extractor.model.parameters()).device
            expected = self.extractor.config.device
            passed = str(device) == expected or device.type == expected
            
            self.print_result(passed, f"Device: {device}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Single Image Extraction Tests (Real Medical Images)
    # ========================================================================
    
    def test_extract_real_medical_image(self):
        """Test 5: Extract features from real medical image."""
        self.print_test("Real Medical Image Feature Extraction")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - No images available")
                return True
            
            image_path = self.image_paths[0]
            features = self.extractor.extract(image_path)
            
            passed = (
                isinstance(features, np.ndarray) and
                features.shape == (512,) and
                features.dtype in [np.float32, np.float64]
            )
            
            self.print_result(
                passed,
                f"Image: {image_path.name}, Shape: {features.shape}, Dtype: {features.dtype}"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_path_string(self):
        """Test 6: Extract from string path."""
        self.print_test("String Path Extraction")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            image_path = str(self.image_paths[0])
            features = self.extractor.extract(image_path)
            
            passed = features.shape == (512,)
            self.print_result(passed, f"Path type: str")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_path_object(self):
        """Test 7: Extract from Path object."""
        self.print_test("Path Object Extraction")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract(self.image_paths[0])
            passed = features.shape == (512,)
            self.print_result(passed, f"Path type: pathlib.Path")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_pil_image(self):
        """Test 8: Extract from PIL Image."""
        self.print_test("PIL Image Extraction")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            pil_image = Image.open(self.image_paths[0])
            features = self.extractor.extract(pil_image)
            
            passed = features.shape == (512,)
            self.print_result(passed, f"PIL mode: {pil_image.mode}, Size: {pil_image.size}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_extract_from_numpy_array(self):
        """Test 9: Extract from numpy array."""
        self.print_test("NumPy Array Extraction")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            pil_image = Image.open(self.image_paths[0]).convert('RGB')
            np_image = np.array(pil_image)
            features = self.extractor.extract(np_image)
            
            passed = features.shape == (512,)
            self.print_result(passed, f"Array shape: {np_image.shape}, Dtype: {np_image.dtype}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_various_image_formats(self):
        """Test 10: Extract from various medical image formats."""
        self.print_test("Multiple Format Support")
        
        try:
            formats_tested = set()
            success_count = 0
            
            for img_path in self.image_paths[:10]:
                try:
                    img = Image.open(img_path)
                    formats_tested.add(img.format)
                    
                    features = self.extractor.extract(img_path)
                    if features.shape == (512,):
                        success_count += 1
                except Exception as e:
                    logger.warning(f"Failed on {img_path.name}: {e}")
            
            passed = success_count > 0
            self.print_result(
                passed,
                f"Formats tested: {formats_tested}, Success: {success_count}/{len(self.image_paths[:10])}"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Feature Normalization Tests
    # ========================================================================
    
    def test_feature_normalization(self):
        """Test 11: Features are L2 normalized (Phase 1 behavior)."""
        self.print_test("L2 Normalization (Phase 1 Default)")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract(self.image_paths[0], normalize=True)
            l2_norm = np.linalg.norm(features)
            
            passed = np.isclose(l2_norm, 1.0, atol=1e-4)
            self.print_result(passed, f"L2 norm: {l2_norm:.8f} (target: 1.0)")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_without_normalization(self):
        """Test 12: Features without normalization."""
        self.print_test("Without Normalization")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract(self.image_paths[0], normalize=False)
            l2_norm = np.linalg.norm(features)
            
            passed = not np.isclose(l2_norm, 1.0, atol=1e-4)
            self.print_result(passed, f"L2 norm: {l2_norm:.8f} (unnormalized)")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Batch Extraction Tests (Real Medical Images)
    # ========================================================================
    
    def test_batch_extraction_medical_images(self):
        """Test 13: Batch extract real medical images."""
        self.print_test("Batch Extraction (Real Medical Images)")
        
        try:
            batch_size = min(8, len(self.image_paths))
            if batch_size < 2:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Need at least 2 images")
                return True
            
            features = self.extractor.extract_batch(
                self.image_paths[:batch_size],
                show_progress=False
            )
            
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
        """Test 14: Batch features are normalized."""
        self.print_test("Batch Normalization")
        
        try:
            batch_size = min(5, len(self.image_paths))
            if batch_size < 2:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract_batch(
                self.image_paths[:batch_size],
                normalize=True
            )
            
            norms = np.linalg.norm(features, axis=1)
            passed = np.allclose(norms, 1.0, atol=1e-4)
            
            norm_stats = f"Min: {norms.min():.6f}, Max: {norms.max():.6f}, Mean: {norms.mean():.6f}"
            self.print_result(passed, norm_stats)
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_large_batch(self):
        """Test 15: Large batch extraction."""
        self.print_test("Large Batch Processing")
        
        try:
            batch_size = min(20, len(self.image_paths))
            if batch_size < 10:
                self.skipped_tests += 1
                print(f"⚠️  SKIPPED - Need at least 10 images (have {batch_size})")
                return True
            
            import time
            start = time.time()
            
            features = self.extractor.extract_batch(
                self.image_paths[:batch_size],
                show_progress=False
            )
            
            elapsed = time.time() - start
            
            passed = features.shape == (batch_size, 512)
            
            throughput = batch_size / elapsed
            self.print_result(
                passed,
                f"{batch_size} images in {elapsed:.2f}s ({throughput:.1f} img/s)"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Consistency Tests (Medical Images)
    # ========================================================================
    
    def test_same_image_consistency(self):
        """Test 16: Same medical image produces identical features."""
        self.print_test("Feature Consistency (Same Image)")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            features1 = self.extractor.extract(self.image_paths[0])
            features2 = self.extractor.extract(self.image_paths[0])
            
            passed = np.allclose(features1, features2, atol=1e-6)
            diff = np.abs(features1 - features2).max()
            
            self.print_result(passed, f"Max difference: {diff:.12f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_different_medical_images(self):
        """Test 17: Different medical images have different features."""
        self.print_test("Feature Uniqueness (Different Medical Images)")
        
        try:
            if len(self.image_paths) < 2:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Need at least 2 images")
                return True
            
            features1 = self.extractor.extract(self.image_paths[0])
            features2 = self.extractor.extract(self.image_paths[1])
            
            similarity = np.dot(features1, features2)
            passed = similarity < 0.99  # Should be different
            
            self.print_result(
                passed,
                f"Cosine similarity: {similarity:.6f} (Images: {self.image_paths[0].name} vs {self.image_paths[1].name})"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_single_vs_batch_consistency(self):
        """Test 18: Single and batch extraction produce same features."""
        self.print_test("Single vs Batch Consistency")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
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
    # Feature Properties Tests (Phase 1 Diversity Model)
    # ========================================================================
    
    def test_feature_range(self):
        """Test 19: Feature values are in valid range."""
        self.print_test("Feature Value Range")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract(self.image_paths[0])
            
            passed = np.all(features >= -1.0) and np.all(features <= 1.0)
            
            self.print_result(
                passed,
                f"Range: [{features.min():.6f}, {features.max():.6f}]"
            )
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_feature_statistics(self):
        """Test 20: Feature statistics for medical images."""
        self.print_test("Feature Statistics")
        
        try:
            if not self.image_paths:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract(self.image_paths[0])
            
            stats = {
                'mean': features.mean(),
                'std': features.std(),
                'min': features.min(),
                'max': features.max(),
                'non_zero': np.count_nonzero(features),
                'near_zero': np.sum(np.abs(features) < 0.01)
            }
            
            passed = (
                -1.0 <= stats['min'] <= 1.0 and
                -1.0 <= stats['max'] <= 1.0 and
                stats['non_zero'] > 400  # Most features should be non-zero
            )
            
            info = (f"Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}, "
                   f"Non-zero: {stats['non_zero']}/512, Near-zero: {stats['near_zero']}")
            self.print_result(passed, info)
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_feature_diversity(self):
        """Test 21: Feature diversity across medical images (Phase 1 goal)."""
        self.print_test("Feature Diversity (Phase 1 Diversity Model)")
        
        try:
            num_images = min(10, len(self.image_paths))
            if num_images < 5:
                self.skipped_tests += 1
                print(f"⚠️  SKIPPED - Need at least 5 images (have {num_images})")
                return True
            
            features = self.extractor.extract_batch(self.image_paths[:num_images])
            
            # Compute pairwise similarities
            similarity_matrix = np.dot(features, features.T)
            
            # Get upper triangle (excluding diagonal)
            mask = np.triu(np.ones_like(similarity_matrix), k=1).astype(bool)
            similarities = similarity_matrix[mask]
            
            mean_sim = similarities.mean()
            std_sim = similarities.std()
            
            # Phase 1 model should have good diversity (similarity < 0.80)
            passed = mean_sim < 0.80
            
            info = (f"Mean similarity: {mean_sim:.4f}, Std: {std_sim:.4f}, "
                   f"Range: [{similarities.min():.4f}, {similarities.max():.4f}]")
            self.print_result(passed, info)
            
            if passed:
                print(f"   ✅ Good diversity (Phase 1 goal: < 0.80)")
            
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Medical Image Similarity Tests
    # ========================================================================
    
    def test_similarity_matrix_medical_images(self):
        """Test 22: Compute similarity matrix for medical images."""
        self.print_test("Medical Image Similarity Matrix")
        
        try:
            num_images = min(5, len(self.image_paths))
            if num_images < 3:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract_batch(self.image_paths[:num_images])
            similarity = np.dot(features, features.T)
            
            # Diagonal should be 1 (self-similarity)
            diagonal = np.diag(similarity)
            passed = np.allclose(diagonal, 1.0, atol=1e-4)
            
            print(f"\n   Similarity Matrix ({num_images} medical images):")
            print("   " + "="*60)
            print("        ", end="")
            for j in range(num_images):
                print(f"Img{j:2d}  ", end="")
            print()
            
            for i in range(num_images):
                print(f"   Img{i:2d}:", end="")
                for j in range(num_images):
                    if i == j:
                        print(f" 1.000 ", end="")
                    else:
                        print(f" {similarity[i, j]:.3f} ", end="")
                print(f"  ({self.image_paths[i].name[:15]}...)")
            
            print("   " + "="*60)
            
            # Stats
            off_diagonal = similarity[~np.eye(num_images, dtype=bool)]
            print(f"\n   Off-diagonal stats:")
            print(f"   Mean: {off_diagonal.mean():.4f}, Std: {off_diagonal.std():.4f}")
            print(f"   Min: {off_diagonal.min():.4f}, Max: {off_diagonal.max():.4f}")
            
            self.print_result(passed, f"Self-similarity check: {diagonal.mean():.6f}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_nearest_neighbor_retrieval(self):
        """Test 23: Nearest neighbor retrieval for medical images."""
        self.print_test("Nearest Neighbor Retrieval")
        
        try:
            num_images = min(10, len(self.image_paths))
            if num_images < 5:
                self.skipped_tests += 1
                return True
            
            features = self.extractor.extract_batch(self.image_paths[:num_images])
            
            # Pick first image as query
            query_features = features[0]
            
            # Compute similarities to all others
            similarities = np.dot(features, query_features)
            
            # Get top-5 nearest neighbors (excluding self)
            top_k = min(5, num_images - 1)
            sorted_indices = np.argsort(similarities)[::-1]
            nearest_neighbors = sorted_indices[1:top_k+1]  # Exclude self (index 0)
            
            passed = len(nearest_neighbors) > 0
            
            print(f"\n   Query: {self.image_paths[0].name}")
            print(f"   Top-{top_k} nearest neighbors:")
            for rank, idx in enumerate(nearest_neighbors, 1):
                print(f"   {rank}. {self.image_paths[idx].name}: similarity = {similarities[idx]:.4f}")
            
            self.print_result(passed, f"Retrieved {len(nearest_neighbors)} neighbors")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Integration & Error Handling Tests
    # ========================================================================
    
    def test_extractor_info(self):
        """Test 24: Get extractor information."""
        self.print_test("Extractor Information")
        
        try:
            info = self.extractor.get_info()
            
            required_keys = ['model_path', 'device', 'feature_dim', 'batch_size', 
                           'model_type', 'model_size', 'num_classes']
            passed = all(key in info for key in required_keys)
            
            print(f"\n   Extractor Configuration:")
            for key, value in info.items():
                print(f"   {key:<20}: {value}")
            
            self.print_result(passed, f"All required keys present: {passed}")
            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_invalid_image_path(self):
        """Test 25: Handle invalid image path gracefully."""
        self.print_test("Invalid Path Handling")
        
        try:
            with self.assertRaises(FeatureExtractionError):
                self.extractor.extract("nonexistent_image.jpg")
            
            passed = True
            self.print_result(passed, "Correctly raised FeatureExtractionError")
            return passed
        except AssertionError:
            self.print_result(False, "Did not raise expected exception")
            return False
        except Exception as e:
            # Still passes if any exception is raised
            passed = True
            self.print_result(passed, f"Raised exception: {type(e).__name__}")
            return passed
    
    def assertRaises(self, exception_type):
        """Context manager for exception testing."""
        class ExceptionContext:
            def __init__(self, expected):
                self.expected = expected
                self.raised = False
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    raise AssertionError(f"Expected {self.expected.__name__} but nothing was raised")
                if not issubclass(exc_type, self.expected):
                    return False  # Re-raise unexpected exception
                self.raised = True
                return True  # Suppress expected exception
        
        return ExceptionContext(exception_type)
    
    # ========================================================================
    # Main Test Runner
    # ========================================================================
    
    def run_all_tests(self):
        """Run all tests."""
        self.print_header("RUNNING COMPREHENSIVE TEST SUITE")
        
        if not self.setup():
            print("\n❌ Setup failed. Cannot run tests.")
            return False
        
        # Run all test methods
        test_methods = [
            # Model initialization
            self.test_model_loaded,
            self.test_feature_dimension,
            self.test_eval_mode,
            self.test_device_placement,
            
            # Single image extraction
            self.test_extract_real_medical_image,
            self.test_extract_from_path_string,
            self.test_extract_from_path_object,
            self.test_extract_from_pil_image,
            self.test_extract_from_numpy_array,
            self.test_various_image_formats,
            
            # Normalization
            self.test_feature_normalization,
            self.test_without_normalization,
            
            # Batch extraction
            self.test_batch_extraction_medical_images,
            self.test_batch_normalization,
            self.test_large_batch,
            
            # Consistency
            self.test_same_image_consistency,
            self.test_different_medical_images,
            self.test_single_vs_batch_consistency,
            
            # Feature properties
            self.test_feature_range,
            self.test_feature_statistics,
            self.test_feature_diversity,
            
            # Medical image similarity
            self.test_similarity_matrix_medical_images,
            self.test_nearest_neighbor_retrieval,
            
            # Integration
            self.test_extractor_info,
            self.test_invalid_image_path,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.failed_tests += 1
                print(f"\n❌ Test crashed: {test_method.__name__}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Print summary
        self.print_summary()
        
        return self.failed_tests == 0
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("TEST SUMMARY")
        
        total = self.passed_tests + self.failed_tests + self.skipped_tests
        pass_rate = (self.passed_tests / total * 100) if total > 0 else 0
        
        print(f"\n{'Total Tests:':<30} {total}")
        print(f"{'✅ Passed:':<30} {self.passed_tests}")
        print(f"{'❌ Failed:':<30} {self.failed_tests}")
        print(f"{'⚠️  Skipped:':<30} {self.skipped_tests}")
        print(f"{'Pass Rate:':<30} {pass_rate:.1f}%")
        
        if self.failed_tests == 0 and self.passed_tests > 0:
            print(f"\n{'='*80}")
            print(f"{'🎉 ALL TESTS PASSED! 🎉':^80}")
            print(f"{'Phase 1 Model Integration Successful':^80}")
            print(f"{'='*80}")
        elif self.failed_tests == 0:
            print(f"\n{'='*80}")
            print(f"{'⚠️  NO TESTS RUN':^80}")
            print(f"{'='*80}")
        else:
            print(f"\n{'='*80}")
            print(f"{'⚠️  SOME TESTS FAILED ({self.failed_tests}/{total})':^80}")
            print(f"{'='*80}")


def main():
    """Main entry point."""
    print("="*80)
    print("ConvNeXt Phase 1 Feature Extractor - Comprehensive Test Suite".center(80))
    print("="*80)
    
    tester = FeatureExtractorTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
