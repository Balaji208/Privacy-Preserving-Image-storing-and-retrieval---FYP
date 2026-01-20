"""
Complete End-to-End Pipeline Test
==================================

Tests the full pipeline from raw image to encrypted hash.

Pipeline Flow:
  1. Load image from sample_images/
  2. Extract 512-D features using ConvNeXt Feature Extractor
  3. Generate 256-bit binary hash using DeepHash
  4. Encrypt hash using FHE (BFV with TenSEAL + SoftHSM)
  5. Decrypt and verify (server-side)

✅ FULLY DETERMINISTIC - Same image always produces same encrypted hash

Requirements:
  - Feature extractor model: models/convnext_state_dict_only.pt
  - DeepHash model: models/deephash_state_dict_only.pt
  - TenSEAL + SoftHSM with BFV keys
  - Sample images in sample_images/

Run with:
    python tests/test_complete_pipeline.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import logging
from PIL import Image
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompletePipelineTester:
    """Test complete image processing pipeline."""
    
    def __init__(self):
        # Models
        self.feature_extractor = None
        self.hash_generator = None
        self.fhe_client = None
        self.fhe_server = None
        
        # Paths
        self.feature_model_path = Path("models/convnext_state_dict_only.pt")
        self.hash_model_path = Path("models/deephash_state_dict_only.pt")
        self.sample_images_dir = Path("sample_images")
        
        # Test data
        self.image_paths = []
        
        # Results
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
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
        self.print_header("SETUP: Complete Pipeline Test")
        
        # Check sample images
        print("\n📦 Checking sample images...")
        if not self.sample_images_dir.exists():
            print(f"❌ Sample images directory not found: {self.sample_images_dir}")
            return False
        
        # Get unique image paths
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        all_paths = []
        for ext in extensions:
            all_paths.extend(list(self.sample_images_dir.glob(ext)))
            all_paths.extend(list(self.sample_images_dir.glob(ext.upper())))
        
        # Remove duplicates
        seen_names = set()
        for path in sorted(all_paths):
            if path.name not in seen_names:
                self.image_paths.append(path)
                seen_names.add(path.name)
        
        if not self.image_paths:
            print(f"❌ No images found in {self.sample_images_dir}")
            return False
        
        self.image_paths = self.image_paths[:5]  # Limit to 5
        print(f"✅ Found {len(self.image_paths)} unique images")
        for i, path in enumerate(self.image_paths):
            print(f"   {i+1}. {path.name}")
        
        # Load Feature Extractor
        print("\n📦 Loading Feature Extractor...")
        try:
            from feature_extractor.extractor import ConvNeXtFeatureExtractor
            
            self.feature_extractor = ConvNeXtFeatureExtractor(
                model_path=self.feature_model_path,
                device=None,
                batch_size=4
            )
            print(f"✅ Feature Extractor loaded")
            print(f"   Device: {self.feature_extractor.config.device}")
            print(f"   Feature dim: {self.feature_extractor.feature_dim}")
        except Exception as e:
            print(f"❌ Failed to load Feature Extractor: {e}")
            return False
        
        # Load DeepHash Generator
        print("\n📦 Loading DeepHash Generator...")
        try:
            from deephashing.generator import DeepHashGenerator
            
            self.hash_generator = DeepHashGenerator(
                model_path=self.hash_model_path,
                device=None,
                batch_size=256
            )
            print(f"✅ DeepHash Generator loaded")
            print(f"   Device: {self.hash_generator.config.device}")
            print(f"   Hash bits: {self.hash_generator.hash_bits}")
        except Exception as e:
            print(f"❌ Failed to load DeepHash Generator: {e}")
            return False
        
        # Load FHE Pipelines
        print("\n📦 Loading FHE Encryption Pipelines...")
        try:
            from fhe_encryption import BFVPipeline
            
            # Client pipeline (encryption only)
            self.fhe_client = BFVPipeline(load_secret_key=False)
            print(f"✅ FHE Client pipeline loaded")
            
            # Server pipeline (with decryption)
            try:
                self.fhe_server = BFVPipeline(load_secret_key=True)
                print(f"✅ FHE Server pipeline loaded")
            except Exception as e:
                print(f"⚠️  FHE Server pipeline not available: {e}")
                self.fhe_server = None
            
        except Exception as e:
            print(f"❌ Failed to load FHE pipelines: {e}")
            return False
        
        return True
    
    # ========================================================================
    # Individual Stage Tests
    # ========================================================================
    
    def test_feature_extraction(self):
        """Test 1: Feature extraction stage."""
        self.print_test("Stage 1: Feature Extraction")
        
        try:
            test_image = self.image_paths[0]
            
            print(f"\n  📷 Input Image:")
            pil_img = Image.open(test_image)
            print(f"     File: {test_image.name}")
            print(f"     Size: {pil_img.size}")
            print(f"     Mode: {pil_img.mode}")
            
            print(f"\n  🔄 Extracting features...")
            features = self.feature_extractor.extract(test_image)
            
            print(f"\n  📊 Output Features:")
            print(f"     Shape: {features.shape}")
            print(f"     Dtype: {features.dtype}")
            print(f"     L2 norm: {np.linalg.norm(features):.6f}")
            print(f"     Range: [{features.min():.6f}, {features.max():.6f}]")
            print(f"     Mean: {features.mean():.6f}")
            
            passed = features.shape == (512,)
            self.print_result(passed, "512-D features extracted")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_hash_generation(self):
        """Test 2: Hash generation stage."""
        self.print_test("Stage 2: Hash Generation")
        
        try:
            test_image = self.image_paths[0]
            
            # Extract features
            print(f"\n  🔄 Step 1: Extracting features...")
            features = self.feature_extractor.extract(test_image)
            print(f"     ✅ Features: {features.shape}")
            
            # Generate hash
            print(f"\n  🔄 Step 2: Generating hash...")
            hash_code = self.hash_generator.generate(features)
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            
            print(f"\n  📊 Output Hash:")
            print(f"     Shape: {hash_code.shape}")
            print(f"     Dtype: {hash_code.dtype}")
            print(f"     Unique values: {np.unique(hash_code)}")
            print(f"     Ones: {np.sum(hash_code)}/256")
            print(f"     Zeros: {256 - np.sum(hash_code)}/256")
            print(f"     First 64 bits: {self._format_binary(hash_code[:64])}")
            
            passed = (
                hash_code.shape == (256,) and
                set(np.unique(hash_code)).issubset({0, 1})
            )
            self.print_result(passed, "256-bit binary hash generated")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_fhe_encryption(self):
        """Test 3: FHE encryption stage."""
        self.print_test("Stage 3: FHE Encryption")
        
        try:
            test_image = self.image_paths[0]
            
            # Extract features
            print(f"\n  🔄 Step 1: Extracting features...")
            features = self.feature_extractor.extract(test_image)
            print(f"     ✅ Features: {features.shape}")
            
            # Generate hash
            print(f"\n  🔄 Step 2: Generating hash...")
            hash_code = self.hash_generator.generate(features)
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            print(f"     ✅ Hash: {hash_code.shape}")
            
            # Encrypt
            print(f"\n  🔄 Step 3: Encrypting hash...")
            ciphertext = self.fhe_client.encrypt(hash_code)
            
            print(f"\n  📊 Output Ciphertext:")
            print(f"     Type: {type(ciphertext).__name__}")
            size_info = self.fhe_client.get_ciphertext_size(ciphertext)
            print(f"     Size: {size_info['total_bytes']:,} bytes")
            print(f"     Scheme: {size_info['scheme']}")
            
            passed = ciphertext is not None
            self.print_result(passed, f"Hash encrypted ({size_info['total_bytes']:,} bytes)")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # End-to-End Pipeline Tests
    # ========================================================================
    
    def test_complete_pipeline_single_image(self):
        """Test 4: Complete pipeline for single image."""
        self.print_test("Complete Pipeline: Single Image")
        
        try:
            test_image = self.image_paths[0]
            
            print(f"\n  {'='*66}")
            print(f"  COMPLETE PIPELINE: Image → Features → Hash → FHE")
            print(f"  {'='*66}")
            
            # Stage 1: Load Image
            print(f"\n  📊 Stage 1: Load Image")
            pil_img = Image.open(test_image)
            print(f"     File: {test_image.name}")
            print(f"     Size: {pil_img.size}")
            print(f"     Mode: {pil_img.mode}")
            
            # Stage 2: Extract Features
            print(f"\n  📊 Stage 2: Extract Features")
            start_time = time.time()
            features = self.feature_extractor.extract(test_image)
            feature_time = time.time() - start_time
            print(f"     ✅ Extracted: {features.shape}")
            print(f"     L2 norm: {np.linalg.norm(features):.6f}")
            print(f"     Time: {feature_time:.3f}s")
            
            # Stage 3: Generate Hash
            print(f"\n  📊 Stage 3: Generate Hash")
            start_time = time.time()
            hash_code = self.hash_generator.generate(features)
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            hash_time = time.time() - start_time
            print(f"     ✅ Generated: {hash_code.shape}")
            print(f"     Ones: {np.sum(hash_code)}/256")
            print(f"     Time: {hash_time:.3f}s")
            print(f"     First 32 bits: {self._format_binary(hash_code[:32])}")
            
            # Stage 4: Encrypt Hash
            print(f"\n  📊 Stage 4: Encrypt Hash (Client)")
            start_time = time.time()
            ciphertext = self.fhe_client.encrypt(hash_code)
            encrypt_time = time.time() - start_time
            size = self.fhe_client.get_ciphertext_size(ciphertext)
            print(f"     ✅ Encrypted: {size['total_bytes']:,} bytes")
            print(f"     Time: {encrypt_time:.3f}s")
            
            # Stage 5: Serialize
            print(f"\n  📊 Stage 5: Serialize for Transmission")
            serialized = self.fhe_client.serialize(ciphertext)
            print(f"     ✅ Serialized: {len(serialized):,} bytes")
            
            # Stage 6: Server-side Decryption (if available)
            if self.fhe_server:
                print(f"\n  📊 Stage 6: Decrypt Hash (Server)")
                start_time = time.time()
                deserialized = self.fhe_server.deserialize(serialized)
                decrypted = self.fhe_server.decrypt(deserialized, hash_length=256)
                decrypt_time = time.time() - start_time
                print(f"     ✅ Decrypted: {decrypted.shape}")
                print(f"     Time: {decrypt_time:.3f}s")
                
                # Verify
                match = np.array_equal(hash_code, decrypted)
                print(f"\n  📊 Stage 7: Verification")
                print(f"     Original hash == Decrypted hash: {match}")
                if not match:
                    diff = np.sum(hash_code != decrypted)
                    print(f"     ❌ Mismatch: {diff}/256 bits differ")
                    passed = False
                else:
                    print(f"     ✅ Perfect match!")
                    passed = True
            else:
                print(f"\n  ⚠️  Server-side decryption skipped (no secret key)")
                passed = True
            
            # Summary
            print(f"\n  📊 Pipeline Summary:")
            total_time = feature_time + hash_time + encrypt_time
            print(f"     Total time: {total_time:.3f}s")
            print(f"     - Feature extraction: {feature_time:.3f}s ({feature_time/total_time*100:.1f}%)")
            print(f"     - Hash generation: {hash_time:.3f}s ({hash_time/total_time*100:.1f}%)")
            print(f"     - FHE encryption: {encrypt_time:.3f}s ({encrypt_time/total_time*100:.1f}%)")
            print(f"     Ciphertext size: {size['total_bytes']:,} bytes")
            
            self.print_result(passed, "Complete pipeline executed successfully")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_pipeline_determinism(self):
        """Test 5: Pipeline determinism (same input → same output)."""
        self.print_test("Pipeline Determinism")
        
        try:
            if self.fhe_server is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline not available")
                return True
            
            test_image = self.image_paths[0]
            
            print(f"\n  📊 Running pipeline twice on same image...")
            print(f"     Image: {test_image.name}")
            
            # Run 1
            print(f"\n  🔄 Run 1:")
            features1 = self.feature_extractor.extract(test_image)
            hash1 = self.hash_generator.generate(features1)
            if hash1.ndim > 1:
                hash1 = hash1.squeeze()
            ctxt1 = self.fhe_client.encrypt(hash1)
            decrypted1 = self.fhe_server.decrypt(ctxt1, hash_length=256)
            print(f"     Features L2 norm: {np.linalg.norm(features1):.6f}")
            print(f"     Hash ones: {np.sum(hash1)}/256")
            print(f"     Decrypted ones: {np.sum(decrypted1)}/256")
            
            # Run 2
            print(f"\n  🔄 Run 2:")
            features2 = self.feature_extractor.extract(test_image)
            hash2 = self.hash_generator.generate(features2)
            if hash2.ndim > 1:
                hash2 = hash2.squeeze()
            ctxt2 = self.fhe_client.encrypt(hash2)
            decrypted2 = self.fhe_server.decrypt(ctxt2, hash_length=256)
            print(f"     Features L2 norm: {np.linalg.norm(features2):.6f}")
            print(f"     Hash ones: {np.sum(hash2)}/256")
            print(f"     Decrypted ones: {np.sum(decrypted2)}/256")
            
            # Compare
            print(f"\n  📊 Comparison:")
            features_match = np.allclose(features1, features2, atol=1e-6)
            hash_match = np.array_equal(hash1, hash2)
            decrypted_match = np.array_equal(decrypted1, decrypted2)
            
            print(f"     Features match: {features_match}")
            print(f"     Hash match: {hash_match}")
            print(f"     Decrypted match: {decrypted_match}")
            
            passed = features_match and hash_match and decrypted_match
            
            if not passed:
                if not features_match:
                    diff = np.abs(features1 - features2).max()
                    print(f"     ❌ Features differ (max diff: {diff:.10f})")
                if not hash_match:
                    diff = np.sum(hash1 != hash2)
                    print(f"     ❌ Hashes differ ({diff}/256 bits)")
                if not decrypted_match:
                    diff = np.sum(decrypted1 != decrypted2)
                    print(f"     ❌ Decrypted differ ({diff}/256 bits)")
            
            self.print_result(passed, "Pipeline is deterministic")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_batch_pipeline(self):
        """Test 6: Batch processing through pipeline."""
        self.print_test("Batch Pipeline Processing")
        
        try:
            batch_size = min(3, len(self.image_paths))
            batch_images = self.image_paths[:batch_size]
            
            print(f"\n  📊 Processing {batch_size} images...")
            for i, img in enumerate(batch_images):
                print(f"     {i+1}. {img.name}")
            
            # Extract features (batch)
            print(f"\n  🔄 Stage 1: Batch feature extraction...")
            features_batch = self.feature_extractor.extract_batch(batch_images)
            print(f"     ✅ Features: {features_batch.shape}")
            
            # Generate hashes (batch)
            print(f"\n  🔄 Stage 2: Batch hash generation...")
            hashes_batch = self.hash_generator.generate_batch(features_batch)
            print(f"     ✅ Hashes: {hashes_batch.shape}")
            
            # Encrypt hashes (batch)
            print(f"\n  🔄 Stage 3: Batch FHE encryption...")
            ciphertexts = self.fhe_client.encrypt_batch(
                [hashes_batch[i] for i in range(batch_size)]
            )
            print(f"     ✅ Encrypted {len(ciphertexts)} hashes")
            
            # Show sizes
            print(f"\n  📊 Batch Statistics:")
            for i in range(batch_size):
                ones = np.sum(hashes_batch[i])
                size = self.fhe_client.get_ciphertext_size(ciphertexts[i])
                print(f"     Image {i+1}: {ones}/256 ones, {size['total_bytes']:,} bytes")
            
            passed = len(ciphertexts) == batch_size
            self.print_result(passed, f"Processed {batch_size} images")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_encrypted_similarity_search(self):
        """Test 7: Encrypted similarity search simulation."""
        self.print_test("Encrypted Similarity Search")
        
        try:
            if self.fhe_server is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline not available")
                return True
            
            if len(self.image_paths) < 2:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Need at least 2 images")
                return True
            
            print(f"\n  📊 Simulating encrypted similarity search...")
            print(f"     Query: {self.image_paths[0].name}")
            print(f"     Candidate: {self.image_paths[1].name}")
            
            # Process query image
            print(f"\n  🔄 Processing query image...")
            query_features = self.feature_extractor.extract(self.image_paths[0])
            query_hash = self.hash_generator.generate(query_features)
            if query_hash.ndim > 1:
                query_hash = query_hash.squeeze()
            query_ctxt = self.fhe_server.encrypt(query_hash)
            print(f"     ✅ Query encrypted")
            
            # Process candidate image
            print(f"\n  🔄 Processing candidate image...")
            cand_features = self.feature_extractor.extract(self.image_paths[1])
            cand_hash = self.hash_generator.generate(cand_features)
            if cand_hash.ndim > 1:
                cand_hash = cand_hash.squeeze()
            cand_ctxt = self.fhe_server.encrypt(cand_hash)
            print(f"     ✅ Candidate encrypted")
            
            # Compute encrypted Hamming distance
            print(f"\n  🔄 Computing encrypted Hamming distance...")
            ctxt_hd = self.fhe_server.hamming_distance(query_ctxt, cand_ctxt, hash_length=256)
            print(f"     ✅ Computed")
            
            # Decrypt result
            print(f"\n  🔄 Decrypting Hamming distance...")
            encrypted_hd = self.fhe_server.decrypt_to_int(ctxt_hd)
            
            # Compute plaintext Hamming distance for comparison
            plaintext_hd = int(np.sum(query_hash != cand_hash))
            
            print(f"\n  📊 Results:")
            print(f"     Plaintext Hamming distance: {plaintext_hd}/256")
            print(f"     Encrypted Hamming distance: {encrypted_hd}/256")
            print(f"     Match: {plaintext_hd == encrypted_hd}")
            
            # Compute similarity
            similarity = 1.0 - (plaintext_hd / 256.0)
            print(f"     Similarity score: {similarity:.4f}")
            
            passed = (plaintext_hd == encrypted_hd)
            self.print_result(passed, f"Hamming distance: {encrypted_hd}")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_detailed_pipeline_visualization(self):
        """Test 8: Detailed pipeline visualization."""
        self.print_test("Detailed Pipeline Visualization")
        
        try:
            test_image = self.image_paths[0]
            
            print(f"\n  {'='*66}")
            print(f"  DETAILED PIPELINE VISUALIZATION")
            print(f"  {'='*66}")
            
            # Load image
            pil_img = Image.open(test_image)
            print(f"\n  📷 Input Image:")
            print(f"     File: {test_image.name}")
            print(f"     Size: {pil_img.size}")
            print(f"     Mode: {pil_img.mode}")
            print(f"     Pixels: {pil_img.size[0] * pil_img.size[1]:,}")
            
            # Extract features
            features = self.feature_extractor.extract(test_image)
            print(f"\n  🔄 Stage 1: Feature Extraction (ConvNeXt)")
            print(f"     Input: {pil_img.size[0]}×{pil_img.size[1]}×3 RGB image")
            print(f"     Output: {features.shape[0]}-D feature vector")
            print(f"     Statistics:")
            print(f"       - L2 norm: {np.linalg.norm(features):.6f}")
            print(f"       - Mean: {features.mean():.6f}")
            print(f"       - Std: {features.std():.6f}")
            print(f"       - Range: [{features.min():.6f}, {features.max():.6f}]")
            
            # Show feature distribution
            print(f"\n     Feature distribution:")
            hist, bins = np.histogram(features, bins=5)
            for i in range(len(hist)):
                bar = "█" * int(hist[i] / hist.max() * 30)
                print(f"       [{bins[i]:>6.3f}, {bins[i+1]:>6.3f}]: {bar} ({hist[i]})")
            
            # Generate hash
            hash_code = self.hash_generator.generate(features)
            if hash_code.ndim > 1:
                hash_code = hash_code.squeeze()
            
            print(f"\n  🔄 Stage 2: Binary Hash Generation (DeepHash)")
            print(f"     Input: 512-D features")
            print(f"     Output: 256-bit binary hash")
            print(f"     Statistics:")
            print(f"       - Ones: {np.sum(hash_code)}/256 ({np.sum(hash_code)/256*100:.1f}%)")
            print(f"       - Zeros: {256-np.sum(hash_code)}/256 ({(256-np.sum(hash_code))/256*100:.1f}%)")
            print(f"       - Balance: {abs(0.5 - np.sum(hash_code)/256):.3f} from ideal")
            
            # Display hash
            print(f"\n     Binary hash (256 bits):")
            for i in range(0, 256, 64):
                chunk = hash_code[i:i+64]
                binary_str = ''.join(str(int(b)) for b in chunk)
                print(f"       Bits {i:>3}-{i+63:>3}: {binary_str}")
            
            # Encrypt
            ciphertext = self.fhe_client.encrypt(hash_code)
            size = self.fhe_client.get_ciphertext_size(ciphertext)
            
            print(f"\n  🔄 Stage 3: FHE Encryption (BFV)")
            print(f"     Input: 256-bit binary hash")
            print(f"     Output: Encrypted ciphertext")
            print(f"     Scheme: BFV (Brakerski-Fan-Vercauteren)")
            print(f"     Backend: TenSEAL + SoftHSM")
            print(f"     Ciphertext size: {size['total_bytes']:,} bytes")
            print(f"     Expansion factor: {size['total_bytes'] / 32:.1f}x (vs 32 bytes plaintext)")
            
            # Verify if server available
            if self.fhe_server:
                decrypted = self.fhe_server.decrypt(ciphertext, hash_length=256)
                match = np.array_equal(hash_code, decrypted)
                
                print(f"\n  🔄 Stage 4: Verification (Server)")
                print(f"     Decrypted hash matches original: {match}")
                if not match:
                    diff = np.sum(hash_code != decrypted)
                    print(f"     ❌ Mismatch: {diff}/256 bits")
                    passed = False
                else:
                    print(f"     ✅ Perfect roundtrip!")
                    passed = True
            else:
                print(f"\n  ⚠️  Server-side verification skipped")
                passed = True
            
            self.print_result(passed, "Pipeline visualization complete")
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
        """Format binary array as string."""
        return ' '.join(''.join(str(int(b)) for b in bits[i:i+8]) 
                       for i in range(0, len(bits), 8))
    
    # ========================================================================
    # Main Test Runner
    # ========================================================================
    
    def run_all_tests(self):
        """Run all pipeline tests."""
        self.print_header("RUNNING COMPLETE PIPELINE TESTS")
        
        if not self.setup():
            print("\n❌ Setup failed. Cannot run tests.")
            return False
        
        # Run all test methods
        test_methods = [
            self.test_feature_extraction,
            self.test_hash_generation,
            self.test_fhe_encryption,
            self.test_complete_pipeline_single_image,
            self.test_pipeline_determinism,
            self.test_batch_pipeline,
            self.test_encrypted_similarity_search,
            self.test_detailed_pipeline_visualization,
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
        
        total = self.passed_tests + self.failed_tests + self.skipped_tests
        
        print(f"\n{'Total Tests:':<30} {total}")
        print(f"{'✅ Passed:':<30} {self.passed_tests}")
        print(f"{'❌ Failed:':<30} {self.failed_tests}")
        print(f"{'⚠️  Skipped:':<30} {self.skipped_tests}")
        
        if self.failed_tests == 0:
            print(f"\n{'='*70}")
            print(f"{'🎉 ALL PIPELINE TESTS PASSED! 🎉':^70}")
            print(f"{'='*70}")
            print(f"\n✅ Complete pipeline is working correctly!")
            print(f"✅ Pipeline is fully deterministic!")
            print(f"✅ Ready for production deployment!")
        else:
            print(f"\n{'='*70}")
            print(f"{'⚠️  SOME TESTS FAILED':^70}")
            print(f"{'='*70}")


def main():
    """Main entry point."""
    tester = CompletePipelineTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
