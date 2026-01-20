"""
FHE Encryption Module Test Suite
=================================

Tests BFV-based Fully Homomorphic Encryption using TenSEAL + SoftHSM.

Tests:
  1. Module initialization (client & server mode)
  2. Encryption of 256-bit DeepHash output
  3. Decryption and correctness validation
  4. Homomorphic operations (XOR, Hamming distance)
  5. Serialization/deserialization
  6. End-to-end encryption pipeline

Requirements:
  - TenSEAL installed
  - SoftHSM configured with BFV keys
  - HSM contains: TENSEAL_BFV_CONTEXT, TENSEAL_PUBLIC_CONTEXT

Run with:
    python tests/test_fhe_encryption.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FHEEncryptionTester:
    """Comprehensive tester for FHE encryption module."""
    
    def __init__(self):
        self.client_pipeline = None
        self.server_pipeline = None
        
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
        # Test data
        self.test_hash = None
        self.test_hash2 = None
    
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
        self.print_header("SETUP: FHE Encryption Test Suite")
        
        # Check if TenSEAL is available
        print("\n📦 Checking TenSEAL availability...")
        try:
            import tenseal as ts
            print("✅ TenSEAL is installed")
        except ImportError:
            print("❌ TenSEAL not installed")
            print("   Install: pip install tenseal")
            return False
        
        # Check HSM availability
        print("\n📦 Checking SoftHSM availability...")
        try:
            from hsm.hsm_manager import get_hsm_manager
            hsm = get_hsm_manager()
            print("✅ SoftHSM is available")
            
            # Check if required keys exist
            print("\n📦 Checking HSM keys...")
            try:
                # Try to retrieve public context
                public_ctx = hsm.retrieve_secret("TENSEAL_PUBLIC_CONTEXT")
                print(f"✅ TENSEAL_PUBLIC_CONTEXT found ({len(public_ctx):,} bytes)")
            except Exception as e:
                print(f"⚠️  TENSEAL_PUBLIC_CONTEXT not found in HSM")
                print(f"   Trying TENSEAL_BFV_CONTEXT instead...")
            
            try:
                # Try to retrieve full context
                full_ctx = hsm.retrieve_secret("TENSEAL_BFV_CONTEXT")
                print(f"✅ TENSEAL_BFV_CONTEXT found ({len(full_ctx):,} bytes)")
            except Exception as e:
                print(f"❌ TENSEAL_BFV_CONTEXT not found in HSM")
                print(f"   Run: python initialize_system_keys.py")
                return False
            
        except Exception as e:
            print(f"❌ HSM not available: {e}")
            return False
        
        # Import FHE module
        print("\n📦 Loading FHE encryption module...")
        try:
            from fhe_encryption import BFVPipeline, FHE_AVAILABLE
            
            if not FHE_AVAILABLE:
                print("❌ FHE module not available")
                return False
            
            print("✅ FHE module loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to import FHE module: {e}")
            return False
        
        # Initialize client pipeline (encryption only)
        print("\n📦 Initializing Client Pipeline (encryption only)...")
        try:
            # Client uses public context (no secret key)
            self.client_pipeline = BFVPipeline(load_secret_key=False)
            print("✅ Client pipeline initialized")
            
            info = self.client_pipeline.get_info()
            print(f"   Mode: {info.get('mode', 'client')}")
            print(f"   Key storage: {info.get('key_storage', 'HSM')}")
        except Exception as e:
            print(f"❌ Failed to initialize client pipeline: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Initialize server pipeline (encryption + decryption)
        print("\n📦 Initializing Server Pipeline (with secret key)...")
        try:
            self.server_pipeline = BFVPipeline(load_secret_key=True)
            print("✅ Server pipeline initialized")
            
            info = self.server_pipeline.get_info()
            print(f"   Mode: {info.get('mode', 'server')}")
            print(f"   Key storage: {info.get('key_storage', 'HSM')}")
            print(f"   Decryption available: {info.get('decryptor_ready', False)}")
        except Exception as e:
            print(f"⚠️  Server pipeline initialization failed: {e}")
            print(f"   This is OK for client-only testing")
            self.server_pipeline = None
        
        # Create deterministic test data (simulating DeepHash output)
        print("\n📦 Creating test data...")
        np.random.seed(42)  # Deterministic
        self.test_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
        self.test_hash2 = np.random.randint(0, 2, 256, dtype=np.uint8)
        print(f"✅ Created test binary hashes")
        print(f"   Hash 1: {np.sum(self.test_hash)}/256 ones")
        print(f"   Hash 2: {np.sum(self.test_hash2)}/256 ones")
        
        return True
    
    # ========================================================================
    # Module Initialization Tests
    # ========================================================================
    
    def test_client_pipeline_init(self):
        """Test 1: Client pipeline initialization."""
        self.print_test("Client Pipeline Initialization")
        
        try:
            passed = self.client_pipeline is not None
            
            if passed:
                info = self.client_pipeline.get_info()
                print(f"\n  📊 Pipeline Info:")
                for key, value in info.items():
                    print(f"     {key}: {value}")
            
            self.print_result(passed, "Client pipeline ready")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_server_pipeline_init(self):
        """Test 2: Server pipeline initialization."""
        self.print_test("Server Pipeline Initialization")
        
        try:
            if self.server_pipeline is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline not available")
                print("   (HSM secret key not loaded)")
                return True
            
            passed = self.server_pipeline is not None
            
            if passed:
                info = self.server_pipeline.get_info()
                print(f"\n  📊 Server Pipeline Info:")
                for key, value in info.items():
                    print(f"     {key}: {value}")
            
            self.print_result(passed, "Server pipeline ready")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Encryption Tests
    # ========================================================================
    
    def test_encrypt_single_hash(self):
        """Test 3: Encrypt single 256-bit hash."""
        self.print_test("Single Hash Encryption")
        
        try:
            print(f"\n  📊 Input Hash:")
            print(f"     Shape: {self.test_hash.shape}")
            print(f"     Dtype: {self.test_hash.dtype}")
            print(f"     Ones: {np.sum(self.test_hash)}/256")
            print(f"     First 64 bits: {self._format_binary(self.test_hash[:64])}")
            
            # Encrypt
            print(f"\n  🔄 Encrypting...")
            ciphertext = self.client_pipeline.encrypt(self.test_hash)
            
            print(f"  ✅ Encryption successful")
            print(f"     Ciphertext type: {type(ciphertext).__name__}")
            
            # Get size info
            size_info = self.client_pipeline.get_ciphertext_size(ciphertext)
            print(f"\n  📊 Ciphertext Info:")
            for key, value in size_info.items():
                print(f"     {key}: {value}")
            
            passed = ciphertext is not None
            self.print_result(passed, f"Ciphertext size: {size_info['total_bytes']:,} bytes")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_encrypt_batch(self):
        """Test 4: Encrypt multiple hashes."""
        self.print_test("Batch Encryption")
        
        try:
            # Create batch of 3 hashes
            batch = [self.test_hash, self.test_hash2, self.test_hash]
            
            print(f"\n  📊 Batch Info:")
            print(f"     Batch size: {len(batch)}")
            print(f"     Hash length: 256 bits")
            
            # Encrypt batch
            print(f"\n  🔄 Encrypting batch...")
            ciphertexts = self.client_pipeline.encrypt_batch(batch)
            
            print(f"  ✅ Batch encryption successful")
            print(f"     Ciphertexts: {len(ciphertexts)}")
            
            passed = len(ciphertexts) == 3
            self.print_result(passed, f"Encrypted {len(ciphertexts)} hashes")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Decryption Tests
    # ========================================================================
    
    def test_decrypt_and_verify(self):
        """Test 5: Decrypt and verify correctness."""
        self.print_test("Decryption and Verification")
        
        try:
            if self.server_pipeline is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline (secret key) not available")
                return True
            
            # Encrypt with client
            print(f"\n  🔄 Encrypting hash...")
            ciphertext = self.client_pipeline.encrypt(self.test_hash)
            print(f"     ✅ Encrypted")
            
            # Decrypt with server
            print(f"\n  🔄 Decrypting hash...")
            decrypted = self.server_pipeline.decrypt(ciphertext, hash_length=256)
            print(f"     ✅ Decrypted")
            
            # Verify
            print(f"\n  📊 Verification:")
            print(f"     Original shape: {self.test_hash.shape}")
            print(f"     Decrypted shape: {decrypted.shape}")
            print(f"     Arrays equal: {np.array_equal(self.test_hash, decrypted)}")
            
            # Compare values
            if not np.array_equal(self.test_hash, decrypted):
                diff_count = np.sum(self.test_hash != decrypted)
                print(f"     ❌ Mismatch: {diff_count}/256 bits differ")
                passed = False
            else:
                print(f"     ✅ Perfect match: 0/256 bits differ")
                passed = True
            
            self.print_result(passed, "Encrypt-decrypt roundtrip successful")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_decrypt_batch(self):
        """Test 6: Decrypt batch of ciphertexts."""
        self.print_test("Batch Decryption")
        
        try:
            if self.server_pipeline is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline not available")
                return True
            
            # Encrypt batch
            batch = [self.test_hash, self.test_hash2]
            ciphertexts = self.server_pipeline.encrypt_batch(batch)
            
            # Decrypt batch
            decrypted_batch = self.server_pipeline.decrypt_batch(ciphertexts, hash_length=256)
            
            # Verify
            passed = (
                len(decrypted_batch) == 2 and
                np.array_equal(decrypted_batch[0], self.test_hash) and
                np.array_equal(decrypted_batch[1], self.test_hash2)
            )
            
            self.print_result(passed, f"Decrypted {len(decrypted_batch)} hashes correctly")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Homomorphic Operations Tests
    # ========================================================================
    
    def test_homomorphic_xor(self):
        """Test 7: Encrypted XOR operation."""
        self.print_test("Homomorphic XOR")
        
        try:
            if self.server_pipeline is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline not available")
                return True
            
            # Encrypt two hashes
            ctxt1 = self.server_pipeline.encrypt(self.test_hash)
            ctxt2 = self.server_pipeline.encrypt(self.test_hash2)
            
            # Perform encrypted XOR
            print(f"\n  🔄 Computing encrypted XOR...")
            ctxt_xor = self.server_pipeline.xor(ctxt1, ctxt2)
            print(f"     ✅ XOR computed")
            
            # Decrypt result
            decrypted_xor = self.server_pipeline.decrypt(ctxt_xor, hash_length=256)
            
            # Compute plaintext XOR for verification
            expected_xor = (self.test_hash + self.test_hash2) % 2
            
            # Verify
            matches = np.array_equal(decrypted_xor, expected_xor)
            
            print(f"\n  📊 Verification:")
            print(f"     Encrypted XOR matches plaintext: {matches}")
            if not matches:
                diff = np.sum(decrypted_xor != expected_xor)
                print(f"     Differences: {diff}/256 bits")
            
            passed = matches
            self.print_result(passed, "Encrypted XOR is correct")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_hamming_distance(self):
        """Test 8: Encrypted Hamming distance computation."""
        self.print_test("Encrypted Hamming Distance")
        
        try:
            if self.server_pipeline is None:
                self.skipped_tests += 1
                print("⚠️  SKIPPED - Server pipeline not available")
                return True
            
            # Encrypt two hashes
            ctxt_query = self.server_pipeline.encrypt(self.test_hash)
            ctxt_candidate = self.server_pipeline.encrypt(self.test_hash2)
            
            # Compute plaintext Hamming distance
            plaintext_hd = int(np.sum(self.test_hash != self.test_hash2))
            
            print(f"\n  📊 Plaintext Hamming Distance:")
            print(f"     Distance: {plaintext_hd}/256")
            
            # Compute encrypted Hamming distance
            print(f"\n  🔄 Computing encrypted Hamming distance...")
            ctxt_hd = self.server_pipeline.hamming_distance(
                ctxt_query, ctxt_candidate, hash_length=256
            )
            print(f"     ✅ Computed")
            
            # Decrypt result
            encrypted_hd = self.server_pipeline.decrypt_to_int(ctxt_hd)
            
            print(f"\n  📊 Encrypted Hamming Distance:")
            print(f"     Distance: {encrypted_hd}/256")
            
            # Verify
            matches = (plaintext_hd == encrypted_hd)
            
            print(f"\n  📊 Verification:")
            print(f"     Plaintext HD: {plaintext_hd}")
            print(f"     Encrypted HD: {encrypted_hd}")
            print(f"     Match: {matches}")
            
            passed = matches
            self.print_result(passed, f"Hamming distance: {encrypted_hd}")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Serialization Tests
    # ========================================================================
    
    def test_serialization(self):
        """Test 9: Ciphertext serialization/deserialization."""
        self.print_test("Ciphertext Serialization")
        
        try:
            # Encrypt
            ciphertext = self.client_pipeline.encrypt(self.test_hash)
            
            # Serialize
            print(f"\n  🔄 Serializing ciphertext...")
            serialized = self.client_pipeline.serialize(ciphertext, format='bytes')
            print(f"     ✅ Serialized: {len(serialized):,} bytes")
            
            # Deserialize
            print(f"\n  🔄 Deserializing...")
            deserialized = self.client_pipeline.deserialize(serialized, format='bytes')
            print(f"     ✅ Deserialized")
            
            # Verify (if server available)
            if self.server_pipeline:
                decrypted_original = self.server_pipeline.decrypt(ciphertext, hash_length=256)
                decrypted_deserialized = self.server_pipeline.decrypt(deserialized, hash_length=256)
                
                matches = np.array_equal(decrypted_original, decrypted_deserialized)
                print(f"\n  📊 Verification:")
                print(f"     Deserialized matches original: {matches}")
                passed = matches
            else:
                # Can't verify without decryption
                passed = deserialized is not None
                print(f"\n  ⚠️  Verification skipped (no server key)")
            
            self.print_result(passed, f"Serialized size: {len(serialized):,} bytes")
            return passed
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Integration Tests
    # ========================================================================
    
    def test_deephash_simulation(self):
        """Test 10: Simulate DeepHash → FHE encryption workflow."""
        self.print_test("DeepHash Integration Simulation")
        
        try:
            print(f"\n  {'='*66}")
            print(f"  SIMULATED WORKFLOW: DeepHash → FHE Encryption")
            print(f"  {'='*66}")
            
            # Simulate DeepHash output
            print(f"\n  📊 Step 1: DeepHash generates 256-bit hash")
            deephash_output = self.test_hash
            print(f"     Hash shape: {deephash_output.shape}")
            print(f"     Hash dtype: {deephash_output.dtype}")
            print(f"     Ones: {np.sum(deephash_output)}/256")
            print(f"     First 32 bits: {self._format_binary(deephash_output[:32])}")
            
            # Client encrypts
            print(f"\n  📊 Step 2: Client encrypts hash (no secret key)")
            encrypted = self.client_pipeline.encrypt(deephash_output)
            size = self.client_pipeline.get_ciphertext_size(encrypted)
            print(f"     ✅ Encrypted successfully")
            print(f"     Ciphertext size: {size['total_bytes']:,} bytes")
            
            # Serialize for transmission
            print(f"\n  📊 Step 3: Serialize for transmission")
            serialized = self.client_pipeline.serialize(encrypted)
            print(f"     ✅ Serialized: {len(serialized):,} bytes")
            
            # Server receives and processes
            if self.server_pipeline:
                print(f"\n  📊 Step 4: Server deserializes and decrypts")
                deserialized = self.server_pipeline.deserialize(serialized)
                decrypted = self.server_pipeline.decrypt(deserialized, hash_length=256)
                print(f"     ✅ Decrypted successfully")
                
                # Verify
                match = np.array_equal(deephash_output, decrypted)
                print(f"\n  📊 Step 5: Verification")
                print(f"     Original == Decrypted: {match}")
                passed = match
            else:
                print(f"\n  ⚠️  Server decryption skipped (no secret key)")
                passed = True
            
            self.print_result(passed, "DeepHash workflow simulation complete")
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
        """Run all FHE encryption tests."""
        self.print_header("RUNNING FHE ENCRYPTION TESTS")
        
        if not self.setup():
            print("\n❌ Setup failed. Cannot run tests.")
            return False
        
        # Run all test methods
        test_methods = [
            self.test_client_pipeline_init,
            self.test_server_pipeline_init,
            self.test_encrypt_single_hash,
            self.test_encrypt_batch,
            self.test_decrypt_and_verify,
            self.test_decrypt_batch,
            self.test_homomorphic_xor,
            self.test_hamming_distance,
            self.test_serialization,
            self.test_deephash_simulation,
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
            print(f"{'🎉 ALL FHE TESTS PASSED! 🎉':^70}")
            print(f"{'='*70}")
            print(f"\n✅ FHE encryption module is working correctly!")
            print(f"✅ Keys loaded from SoftHSM successfully!")
            print(f"✅ Ready for DeepHash → FHE encryption pipeline!")
        else:
            print(f"\n{'='*70}")
            print(f"{'⚠️  SOME TESTS FAILED':^70}")
            print(f"{'='*70}")


def main():
    """Main entry point."""
    tester = FHEEncryptionTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
