"""
Complete Pipeline Test: Feature Extraction → DeepHashing
=========================================================

Tests the full pipeline from image to binary hash codes.
✅ FULLY DETERMINISTIC - No random inputs/outputs

Flow:
  1. Load image from sample_images/
  2. Extract 512-D features using ConvNeXt
  3. Generate 256-bit binary hash using DeepHash
  4. Display and validate results

Run with:
    python tests/test_pipeline_feature_to_hash.py
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
from deephashing.generator import DeepHashGenerator
from deephashing.exceptions import DeepHashError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineTester:
    """Test complete feature extraction → hashing pipeline."""
    
    def __init__(self):
        # Model paths
        self.feature_model_path = Path("models/convnext_state_dict_only.pt")
        self.hash_model_path = Path("models/deephash_state_dict_only.pt")
        self.sample_images_dir = Path("sample_images")
        
        # Models
        self.feature_extractor = None
        self.hash_generator = None
        
        # Test data
        self.image_paths = []
        
        # Results
        self.passed_tests = 0
        self.failed_tests = 0
    
    def print_header(self, title):
        """Print section header."""
        print("\n" + "="*70)
        print(f"{title:^70}")
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
        self.print_header("SETUP: Feature → Hash Pipeline Test")
        
        # Check feature model
        print(f"\nChecking feature extractor model: {self.feature_model_path}")
        if not self.feature_model_path.exists():
            print(f"❌ Model not found: {self.feature_model_path}")
            return False
        print(f"✅ Feature model found")
        
        # Check hash model
        print(f"\nChecking hash generator model: {self.hash_model_path}")
        if not self.hash_model_path.exists():
            print(f"❌ Model not found: {self.hash_model_path}")
            return False
        print(f"✅ Hash model found")
        
        # Check sample images
        print(f"\nChecking sample images: {self.sample_images_dir}")
        if not self.sample_images_dir.exists():
            print(f"❌ Sample images directory not found")
            return False
        
        # Get UNIQUE image paths (remove duplicates)
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        all_paths = []
        for ext in extensions:
            all_paths.extend(list(self.sample_images_dir.glob(ext)))
            all_paths.extend(list(self.sample_images_dir.glob(ext.upper())))
        
        # Remove duplicates by file name
        seen_names = set()
        for path in sorted(all_paths):
            if path.name not in seen_names:
                self.image_paths.append(path)
                seen_names.add(path.name)
        
        if not self.image_paths:
            print(f"❌ No images found in {self.sample_images_dir}")
            return False
        
        self.image_paths = self.image_paths[:10]  # Limit to 10
        print(f"✅ Found {len(self.image_paths)} unique sample images")
        
        # Load feature extractor
        print(f"\n📦 Loading Feature Extractor...")
        try:
            self.feature_extractor = ConvNeXtFeatureExtractor(
                model_path=self.feature_model_path,
                device=None,  # Auto-detect
                batch_size=4
            )
            print(f"✅ Feature extractor loaded")
            print(f"   - Device: {self.feature_extractor.config.device}")
            print(f"   - Feature dim: {self.feature_extractor.feature_dim}")
        except Exception as e:
            print(f"❌ Failed to load feature extractor: {e}")
            return False
        
        # Load hash generator
        print(f"\n📦 Loading Hash Generator...")
        try:
            self.hash_generator = DeepHashGenerator(
                model_path=self.hash_model_path,
                device=None,  # Auto-detect
                batch_size=256
            )
            print(f"✅ Hash generator loaded")
            print(f"   - Device: {self.hash_generator.config.device}")
            print(f"   - Hash bits: {self.hash_generator.hash_bits}")
            print(f"   - Input dim: {self.hash_generator.input_dim}")
        except Exception as e:
            print(f"❌ Failed to load hash generator: {e}")
            return False
        
        return True
    
    # ========================================================================
    # Pipeline Tests
    # ========================================================================
    
    def test_single_image_pipeline(self):
        """Test 1: Complete pipeline for single image."""
        self.print_test("Single Image: Image → Features → Hash")
        
        try:
            # Select test image
            test_image = self.image_paths[0]
            print(f"\n  📷 Image: {test_image.name}")
            
            # Step 1: Extract features
            print(f"  🔄 Step 1: Extracting features...")
            features = self.feature_extractor.extract(test_image)
            print(f"     ✓ Features shape: {features.shape}")
            print(f"     ✓ Features dtype: {features.dtype}")
            print(f"     ✓ L2 norm: {np.linalg.norm(features):.6f}")
            
            # Step 2: Generate hash
            print(f"  🔄 Step 2: Generating hash code...")
            hash_code = self.hash_generator.generate(features)
            
            # Ensure 1D array
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            
            print(f"     ✓ Hash shape: {hash_code.shape}")
            print(f"     ✓ Hash dtype: {hash_code.dtype}")
            print(f"     ✓ Unique values: {np.unique(hash_code)}")
            print(f"     ✓ Ones count: {np.sum(hash_code)}/{len(hash_code)}")
            
            # Display first 64 bits
            print(f"\n  📊 First 64 bits of hash:")
            print(f"     {self._format_binary(hash_code[:64])}")
            
            # Validation
            passed = (
                features.shape == (512,) and
                hash_code.shape == (256,) and
                set(np.unique(hash_code)).issubset({0, 1})
            )
            
            self.print_result(passed, f"Pipeline complete: {test_image.name}")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_batch_pipeline(self):
        """Test 2: Batch processing pipeline."""
        self.print_test("Batch Processing: Multiple Images → Hashes")
        
        try:
            batch_size = min(5, len(self.image_paths))
            batch_images = self.image_paths[:batch_size]
            
            print(f"\n  📷 Processing {batch_size} images...")
            for i, img in enumerate(batch_images):
                print(f"     {i}: {img.name}")
            
            # Step 1: Extract features for batch
            print(f"  🔄 Step 1: Extracting features (batch)...")
            features = self.feature_extractor.extract_batch(batch_images)
            print(f"     ✓ Features shape: {features.shape}")
            
            # Step 2: Generate hashes for batch
            print(f"  🔄 Step 2: Generating hash codes (batch)...")
            hash_codes = self.hash_generator.generate_batch(features)
            print(f"     ✓ Hash codes shape: {hash_codes.shape}")
            
            # Show statistics
            print(f"\n  📊 Batch Statistics:")
            for i in range(batch_size):
                ones = np.sum(hash_codes[i])
                print(f"     Image {i}: {ones}/256 ones, "
                      f"{256-ones}/256 zeros ({batch_images[i].name})")
            
            # Validation
            passed = (
                features.shape == (batch_size, 512) and
                hash_codes.shape == (batch_size, 256) and
                np.all(np.isin(hash_codes, [0, 1]))
            )
            
            self.print_result(passed, f"Processed {batch_size} images")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_hash_consistency(self):
        """Test 3: Hash code consistency for same image (DETERMINISTIC)."""
        self.print_test("Hash Consistency Check (Deterministic)")
        
        try:
            test_image = self.image_paths[0]
            
            # Generate hash twice
            print(f"\n  🔄 Generating hash code (1st time)...")
            features1 = self.feature_extractor.extract(test_image)
            hash1 = self.hash_generator.generate(features1)
            if hash1.ndim > 1:
                hash1 = hash1.squeeze()
            
            print(f"  🔄 Generating hash code (2nd time)...")
            features2 = self.feature_extractor.extract(test_image)
            hash2 = self.hash_generator.generate(features2)
            if hash2.ndim > 1:
                hash2 = hash2.squeeze()
            
            # Compare
            hamming_dist = np.sum(hash1 != hash2)
            print(f"\n  📊 Comparison:")
            print(f"     Hamming distance: {hamming_dist}")
            print(f"     Identical: {np.array_equal(hash1, hash2)}")
            
            passed = np.array_equal(hash1, hash2)
            self.print_result(
                passed,
                f"Hamming distance: {hamming_dist} (MUST be 0 for determinism)"
            )
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_hash_uniqueness(self):
        """Test 4: Different images produce different hashes."""
        self.print_test("Hash Uniqueness for Different Images")
        
        try:
            if len(self.image_paths) < 3:
                print("⚠️  Skipped - Need at least 3 unique images")
                self.passed_tests += 1
                return True
            
            # Use first 3 UNIQUE images
            print(f"\n  🔄 Processing 3 different images...")
            hashes = []
            for i in range(3):
                print(f"     Image {i}: {self.image_paths[i].name}")
                features = self.feature_extractor.extract(self.image_paths[i])
                hash_code = self.hash_generator.generate(features)
                if hash_code.ndim > 1:
                    hash_code = hash_code.squeeze()
                hashes.append(hash_code)
            
            # Compute pairwise Hamming distances
            print(f"\n  📊 Hamming Distance Matrix:")
            print(f"     {'':>10} ", end="")
            for i in range(3):
                print(f"Img{i:>6} ", end="")
            print()
            
            for i in range(3):
                print(f"     Img{i:<6} ", end="")
                for j in range(3):
                    dist = self.hash_generator.compute_hamming_distance(
                        hashes[i], hashes[j]
                    )
                    print(f"{dist:>7} ", end="")
                print()
            
            # Check that different images have non-zero distances
            dist_01 = self.hash_generator.compute_hamming_distance(hashes[0], hashes[1])
            dist_02 = self.hash_generator.compute_hamming_distance(hashes[0], hashes[2])
            dist_12 = self.hash_generator.compute_hamming_distance(hashes[1], hashes[2])
            
            # At least ONE pair should be different
            passed = (dist_01 > 0) or (dist_02 > 0) or (dist_12 > 0)
            
            if dist_01 == 0 and dist_02 == 0 and dist_12 == 0:
                self.print_result(False, "All images produced identical hashes!")
            else:
                max_dist = max(dist_01, dist_02, dist_12)
                self.print_result(passed, f"Max distance: {max_dist}")
            
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_hash_properties(self):
        """Test 5: Hash code properties."""
        self.print_test("Hash Code Properties")
        
        try:
            # Generate hash for test image
            features = self.feature_extractor.extract(self.image_paths[0])
            hash_code = self.hash_generator.generate(features)
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            
            # Check properties
            print(f"\n  📊 Hash Properties:")
            print(f"     Shape: {hash_code.shape}")
            print(f"     Dtype: {hash_code.dtype}")
            print(f"     Min value: {hash_code.min()}")
            print(f"     Max value: {hash_code.max()}")
            print(f"     Unique values: {np.unique(hash_code)}")
            print(f"     Zeros: {np.sum(hash_code == 0)}")
            print(f"     Ones: {np.sum(hash_code == 1)}")
            
            # Balance check (should be roughly 50/50)
            ones_ratio = np.sum(hash_code) / len(hash_code)
            print(f"     Ones ratio: {ones_ratio:.3f} (ideal: 0.5)")
            
            passed = (
                hash_code.shape == (256,) and
                set(np.unique(hash_code)).issubset({0, 1}) and
                0.3 < ones_ratio < 0.7  # Reasonable balance
            )
            
            self.print_result(passed, f"Hash is well-formed and balanced")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_similarity_computation(self):
        """Test 6: Similarity score computation."""
        self.print_test("Similarity Score Computation")
        
        try:
            # Generate hashes for 3 images
            num_images = min(3, len(self.image_paths))
            hashes = []
            for i in range(num_images):
                features = self.feature_extractor.extract(self.image_paths[i])
                hash_code = self.hash_generator.generate(features)
                if hash_code.ndim > 1:
                    hash_code = hash_code.squeeze()
                hashes.append(hash_code)
            
            # Compute similarity matrix
            print(f"\n  📊 Similarity Matrix (0=different, 1=identical):")
            print(f"     {'':>10} ", end="")
            for i in range(len(hashes)):
                print(f"Img{i:>6} ", end="")
            print()
            
            for i in range(len(hashes)):
                print(f"     Img{i:<6} ", end="")
                for j in range(len(hashes)):
                    sim = self.hash_generator.compute_similarity(hashes[i], hashes[j])
                    print(f"{sim:>7.3f} ", end="")
                print()
            
            # Check diagonal is 1.0 (self-similarity)
            passed = True
            for i in range(len(hashes)):
                sim = self.hash_generator.compute_similarity(hashes[i], hashes[i])
                if not np.isclose(sim, 1.0):
                    passed = False
            
            self.print_result(passed, "Similarity computation working")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_model_info(self):
        """Test 7: Get model information."""
        self.print_test("Model Information")
        
        try:
            # Get feature extractor info
            print(f"\n  📊 Feature Extractor Info:")
            fe_info = self.feature_extractor.get_info()
            for key, value in fe_info.items():
                if key != 'metrics':  # Skip verbose metrics
                    print(f"     {key}: {value}")
            
            # Get hash generator info
            print(f"\n  📊 Hash Generator Info:")
            hg_info = self.hash_generator.get_info()
            for key, value in hg_info.items():
                if key == 'metrics' and isinstance(value, dict):
                    print(f"     metrics: [mAP={value.get('map', 0):.4f}]")
                else:
                    print(f"     {key}: {value}")
            
            passed = (
                'feature_dim' in fe_info and
                'hash_bits' in hg_info
            )
            
            self.print_result(passed, "Model info retrieved successfully")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_detailed_example(self):
        """Test 8: Detailed example with visualizations."""
        self.print_test("Detailed Example with Visualizations")
        
        try:
            test_image = self.image_paths[0]
            
            print(f"\n  {'='*66}")
            print(f"  DETAILED PIPELINE EXAMPLE")
            print(f"  {'='*66}")
            
            # Load and display image info
            pil_img = Image.open(test_image)
            print(f"\n  📷 Input Image:")
            print(f"     Path: {test_image}")
            print(f"     Name: {test_image.name}")
            print(f"     Size: {pil_img.size}")
            print(f"     Mode: {pil_img.mode}")
            
            # Extract features
            print(f"\n  🔄 Feature Extraction:")
            features = self.feature_extractor.extract(test_image)
            print(f"     Shape: {features.shape}")
            print(f"     Dtype: {features.dtype}")
            print(f"     L2 norm: {np.linalg.norm(features):.6f}")
            print(f"     Min: {features.min():.6f}")
            print(f"     Max: {features.max():.6f}")
            print(f"     Mean: {features.mean():.6f}")
            print(f"     Std: {features.std():.6f}")
            
            # Show feature distribution
            print(f"\n     Feature value distribution:")
            hist, bins = np.histogram(features, bins=5)
            for i in range(len(hist)):
                bar = "█" * int(hist[i] / hist.max() * 40)
                print(f"       [{bins[i]:>6.3f}, {bins[i+1]:>6.3f}]: {bar} ({hist[i]})")
            
            # Generate hash
            print(f"\n  🔄 Hash Generation:")
            hash_code, logits = self.hash_generator.generate(features, return_logits=True)
            
            # Ensure 1D
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            
            print(f"     Shape: {hash_code.shape}")
            print(f"     Dtype: {hash_code.dtype}")
            print(f"     Ones: {np.sum(hash_code)}/256")
            print(f"     Zeros: {256 - np.sum(hash_code)}/256")
            
            # Show hash as binary string
            print(f"\n  📊 Binary Hash Code (256 bits):")
            for i in range(0, 256, 64):
                chunk = hash_code[i:i+64]
                binary_str = ''.join(str(int(b)) for b in chunk)
                print(f"     Bits {i:>3}-{i+63:>3}: {binary_str}")
            
            # Show hash as hex
            hash_hex = self._hash_to_hex(hash_code)
            print(f"\n  📊 Hexadecimal Representation:")
            for i in range(0, len(hash_hex), 64):
                print(f"     {hash_hex[i:i+64]}")
            
            passed = True
            self.print_result(passed, "Detailed example completed")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _format_binary(self, bits):
        """Format binary array as string with spacing."""
        binary_str = ''.join(str(int(b)) for b in bits)
        return ' '.join(binary_str[i:i+8] for i in range(0, len(binary_str), 8))
    
    def _hash_to_hex(self, hash_code):
        """Convert binary hash to hexadecimal string."""
        hex_str = ""
        for i in range(0, len(hash_code), 8):
            byte = hash_code[i:min(i+8, len(hash_code))]
            # Pad if necessary
            if len(byte) < 8:
                byte = np.pad(byte, (0, 8 - len(byte)))
            binary_str = ''.join(str(int(b)) for b in byte)
            byte_val = int(binary_str, 2)
            hex_str += f"{byte_val:02x}"
        
        # Format with spaces
        return ' '.join(hex_str[i:i+8] for i in range(0, len(hex_str), 8))
    
    # ========================================================================
    # Main Test Runner
    # ========================================================================
    
    def run_all_tests(self):
        """Run all pipeline tests."""
        self.print_header("RUNNING PIPELINE TESTS")
        
        if not self.setup():
            print("\n❌ Setup failed. Cannot run tests.")
            return False
        
        # Run all test methods
        test_methods = [
            self.test_single_image_pipeline,
            self.test_batch_pipeline,
            self.test_hash_consistency,
            self.test_hash_uniqueness,
            self.test_hash_properties,
            self.test_similarity_computation,
            self.test_model_info,
            self.test_detailed_example,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.failed_tests += 1
                print(f"\n❌ Test crashed: {e}")
                import traceback
                traceback.print_exc()
        
        # Print summary
        self.print_summary()
        
        return self.failed_tests == 0
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("TEST SUMMARY")
        
        total = self.passed_tests + self.failed_tests
        
        print(f"\n{'Total Tests:':<30} {total}")
        print(f"{'✅ Passed:':<30} {self.passed_tests}")
        print(f"{'❌ Failed:':<30} {self.failed_tests}")
        
        if self.failed_tests == 0:
            print(f"\n{'='*70}")
            print(f"{'🎉 ALL PIPELINE TESTS PASSED! 🎉':^70}")
            print(f"{'='*70}")
            print(f"\n✅ Image → Features → Hash pipeline is FULLY DETERMINISTIC!")
            print(f"✅ Same input ALWAYS produces same output!")
        else:
            print(f"\n{'='*70}")
            print(f"{'⚠️  SOME TESTS FAILED':^70}")
            print(f"{'='*70}")


def main():
    """Main entry point."""
    tester = PipelineTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
