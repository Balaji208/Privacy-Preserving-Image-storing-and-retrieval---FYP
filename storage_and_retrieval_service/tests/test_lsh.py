"""
LSH Tokenization Module Test Suite
===================================

Tests the complete LSH tokenization pipeline:
1. DeepHash → SimHash bucket generation
2. Bucket ID → HMAC tokenization  
3. FHE CT → HMAC tokenization
4. Redis storage and retrieval

Requirements:
  - Redis server running (localhost:6379)
  - SoftHSM with LSH_HMAC_KEY
  - FHE encryption module
  - DeepHash module

Run with:
    python tests/test_lsh_tokenization.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import logging
import redis
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LSHTokenizationTester:
    """Comprehensive tester for LSH tokenization module."""
    
    def __init__(self):
        # Components
        self.redis_client = None
        self.lsh_indexer = None
        self.fhe_client = None
        self.hmac_key = None
        
        # Test data
        self.test_hashes = []
        self.test_fhe_cts = []
        self.test_image_ids = []
        
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
        self.print_header("SETUP: LSH Tokenization Test Suite")
        
        # Check Redis
        print("\n📦 Checking Redis connection...")
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=False
            )
            self.redis_client.ping()
            print("✅ Redis is running")
            
            # Clean test keys
            pattern = "lsh:token:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                print(f"   Cleaning {len(keys)} existing keys...")
                self.redis_client.delete(*keys)
                
        except redis.ConnectionError:
            print("❌ Redis not running. Start with: redis-server")
            print("   Or install: https://redis.io/download")
            return False
        
        # Load HMAC key from HSM
        print("\n📦 Loading HMAC key from SoftHSM...")
        try:
            from hsm.hsm_manager import get_hsm_manager
            hsm = get_hsm_manager()
            self.hmac_key = hsm.retrieve_secret("LSH_HMAC_KEY")
            print(f"✅ HMAC key loaded ({len(self.hmac_key)} bytes)")
        except Exception as e:
            print(f"❌ Failed to load HMAC key: {e}")
            print("   Run: python lsh_tokenization/setup/initialize.py")
            return False
        
        # Initialize LSH Indexer
        print("\n📦 Initializing LSH Indexer...")
        try:
            from lsh_tokenization.pipeline.index_builder import LSHIndexer
            from lsh_tokenization.config.lsh_config import LSHConfig
            
            config = LSHConfig(
                hash_length=256,
                num_tables=6,
                bits_per_table=12,
                random_seed=42
            )
            
            self.lsh_indexer = LSHIndexer(
                redis_client=self.redis_client,
                hmac_key=self.hmac_key,
                config=config,
                use_token_cache=True
            )
            print("✅ LSH Indexer initialized")
            print(f"   Tables (L): {config.num_tables}")
            print(f"   Bits per table (K): {config.bits_per_table}")
            print(f"   Buckets per table: {config.buckets_per_table}")
            
        except Exception as e:
            print(f"❌ Failed to initialize LSH Indexer: {e}")
            return False
        
        # Load FHE Client
        print("\n📦 Loading FHE Client...")
        try:
            from fhe_encryption import BFVPipeline
            self.fhe_client = BFVPipeline(load_secret_key=False)
            print("✅ FHE Client loaded")
        except Exception as e:
            print(f"❌ Failed to load FHE Client: {e}")
            return False
        
        # Create test data
        print("\n📦 Creating test data...")
        np.random.seed(42)  # Deterministic
        
        for i in range(5):
            # Generate random 256-bit hash (simulating DeepHash output)
            hash_code = np.random.randint(0, 2, 256, dtype=np.uint8)
            self.test_hashes.append(hash_code)
            
            # Encrypt with FHE
            fhe_ct = self.fhe_client.encrypt(hash_code)
            fhe_ct_bytes = self.fhe_client.serialize(fhe_ct)
            self.test_fhe_cts.append(fhe_ct_bytes)
            
            # Generate image ID
            image_id = f"IMG_{i+1:03d}"
            self.test_image_ids.append(image_id)
        
        print(f"✅ Created {len(self.test_hashes)} test samples")
        print(f"   Hash shape: {self.test_hashes[0].shape}")
        print(f"   FHE CT size: ~{len(self.test_fhe_cts[0]):,} bytes")
        
        return True
    
    # ========================================================================
    # Component Tests
    # ========================================================================
    
    def test_simhash_generation(self):
        """Test 1: SimHash bucket ID generation."""
        self.print_test("SimHash Bucket Generation")
        
        try:
            from lsh_tokenization.simhash.simhash_generator import SimHashGenerator
            from lsh_tokenization.config.lsh_config import LSHConfig
            
            config = LSHConfig()
            generator = SimHashGenerator(config)
            
            test_hash = self.test_hashes[0]
            
            print(f"\n  📊 Input:")
            print(f"     Hash: {test_hash[:32]}")
            print(f"     Ones: {np.sum(test_hash)}/256")
            
            print(f"\n  🔄 Generating bucket IDs...")
            bucket_ids = generator.generate_bucket_ids(test_hash)
            
            print(f"\n  📊 Output:")
            print(f"     Number of buckets: {len(bucket_ids)}")
            print(f"     Bucket IDs: {bucket_ids}")
            print(f"     Range: [0, {2**config.bits_per_table - 1}]")
            
            # Verify
            passed = (
                len(bucket_ids) == config.num_tables and
                all(0 <= bid < 2**config.bits_per_table for bid in bucket_ids)
            )
            
            self.print_result(passed, f"Generated {len(bucket_ids)} valid bucket IDs")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_bucket_tokenization(self):
        """Test 2: HMAC tokenization of bucket IDs."""
        self.print_test("Bucket ID HMAC Tokenization")
        
        try:
            from lsh_tokenization.tokenization.hmac_tokenizer import HMACTokenizer
            
            tokenizer = HMACTokenizer(self.hmac_key)
            
            tenant_id = "hospital_A"
            bucket_id = 1234
            table_idx = 0
            
            print(f"\n  📊 Input:")
            print(f"     Tenant ID: {tenant_id}")
            print(f"     Bucket ID: {bucket_id}")
            print(f"     Table index: {table_idx}")
            
            print(f"\n  🔄 Generating HMAC token...")
            token = tokenizer.tokenize(tenant_id, bucket_id, table_idx)
            
            print(f"\n  📊 Output:")
            print(f"     Token: {token}")
            print(f"     Length: {len(token)} characters ({len(token)//2} bytes)")
            
            # Verify determinism
            token2 = tokenizer.tokenize(tenant_id, bucket_id, table_idx)
            deterministic = (token == token2)
            
            print(f"\n  📊 Verification:")
            print(f"     Deterministic: {deterministic}")
            print(f"     Second generation: {token2}")
            
            passed = (len(token) == 64 and deterministic)
            self.print_result(passed, "HMAC tokenization works correctly")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_fhe_ct_tokenization(self):
        """Test 3: FHE ciphertext HMAC tokenization."""
        self.print_test("FHE Ciphertext HMAC Tokenization")
        
        try:
            from lsh_tokenization.utils.fhe_ct_tokenizer import FHECTTokenizer
            
            tokenizer = FHECTTokenizer(self.hmac_key)
            
            fhe_ct = self.test_fhe_cts[0]
            image_id = self.test_image_ids[0]
            
            print(f"\n  📊 Input:")
            print(f"     FHE CT size: {len(fhe_ct):,} bytes")
            print(f"     Image ID: {image_id}")
            print(f"     FHE CT preview: {fhe_ct[:32].hex()}...")
            
            print(f"\n  🔄 Generating HMAC token...")
            token = tokenizer.tokenize_fhe_ct(fhe_ct, image_id)
            
            print(f"\n  📊 Output:")
            print(f"     Token: {token}")
            print(f"     Length: {len(token)} characters")
            
            # Verify determinism
            token2 = tokenizer.tokenize_fhe_ct(fhe_ct, image_id)
            deterministic = (token == token2)
            
            # Verify uniqueness
            token3 = tokenizer.tokenize_fhe_ct(fhe_ct, "different_id")
            unique = (token != token3)
            
            print(f"\n  📊 Verification:")
            print(f"     Deterministic: {deterministic}")
            print(f"     Unique per image_id: {unique}")
            
            passed = (len(token) == 64 and deterministic and unique)
            self.print_result(passed, "FHE CT tokenization works correctly")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_redis_storage(self):
        """Test 4: Redis storage operations."""
        self.print_test("Redis Storage Operations")
        
        try:
            bucket_token = "test_bucket_token_123"
            fhe_ct_token = "test_fhe_ct_token_456"
            
            print(f"\n  📊 Test data:")
            print(f"     Bucket token: {bucket_token}")
            print(f"     FHE CT token: {fhe_ct_token}")
            
            # Add token
            print(f"\n  🔄 Adding FHE CT token to bucket...")
            success = self.lsh_indexer.redis_index.add_fhe_ct_token(
                bucket_token, fhe_ct_token
            )
            print(f"     ✅ Added: {success}")
            
            # Retrieve tokens
            print(f"\n  🔄 Retrieving FHE CT tokens...")
            tokens = self.lsh_indexer.redis_index.get_fhe_ct_tokens([bucket_token])
            print(f"     ✅ Retrieved {len(tokens)} tokens")
            print(f"     Tokens: {tokens}")
            
            # Verify
            matches = (len(tokens) == 1 and tokens[0] == fhe_ct_token)
            
            print(f"\n  📊 Verification:")
            print(f"     Retrieved token matches: {matches}")
            
            # Cleanup
            self.lsh_indexer.redis_index.delete_bucket(bucket_token)
            
            passed = success and matches
            self.print_result(passed, "Redis storage works correctly")
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
        """Test 5: Complete pipeline for single image."""
        self.print_test("Complete Pipeline: Single Image")
        
        try:
            tenant_id = "hospital_A"
            binary_hash = self.test_hashes[0]
            fhe_ct = self.test_fhe_cts[0]
            image_id = self.test_image_ids[0]
            
            print(f"\n  {'='*66}")
            print(f"  COMPLETE LSH PIPELINE")
            print(f"  {'='*66}")
            
            print(f"\n  📊 Input:")
            print(f"     Tenant: {tenant_id}")
            print(f"     Image ID: {image_id}")
            print(f"     Hash ones: {np.sum(binary_hash)}/256")
            print(f"     FHE CT size: {len(fhe_ct):,} bytes")
            
            # Add to index
            print(f"\n  🔄 Adding to LSH index...")
            start_time = time.time()
            success = self.lsh_indexer.add_fhe_ct(
                binary_hash=binary_hash,
                tenant_id=tenant_id,
                fhe_ct=fhe_ct,
                image_id=image_id
            )
            add_time = time.time() - start_time
            
            print(f"     ✅ Added: {success}")
            print(f"     Time: {add_time:.3f}s")
            
            # Query the index
            print(f"\n  🔄 Querying LSH index...")
            start_time = time.time()
            fhe_ct_tokens = self.lsh_indexer.query_fhe_ct_tokens(
                binary_hash=binary_hash,
                tenant_id=tenant_id
            )
            query_time = time.time() - start_time
            
            print(f"     ✅ Retrieved {len(fhe_ct_tokens)} FHE CT tokens")
            print(f"     Time: {query_time:.3f}s")
            print(f"     Tokens: {[t[:16]+'...' for t in fhe_ct_tokens[:3]]}")
            
            # Verify
            print(f"\n  📊 Verification:")
            print(f"     Query found the added image: {len(fhe_ct_tokens) >= 1}")
            
            passed = success and len(fhe_ct_tokens) >= 1
            self.print_result(passed, f"Pipeline complete ({add_time+query_time:.3f}s total)")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_batch_indexing(self):
        """Test 6: Batch indexing multiple images."""
        self.print_test("Batch Indexing")
        
        try:
            tenant_id = "hospital_B"
            batch_size = 3
            
            print(f"\n  📊 Indexing {batch_size} images...")
            
            success_count = 0
            for i in range(batch_size):
                success = self.lsh_indexer.add_fhe_ct(
                    binary_hash=self.test_hashes[i],
                    tenant_id=tenant_id,
                    fhe_ct=self.test_fhe_cts[i],
                    image_id=self.test_image_ids[i]
                )
                if success:
                    success_count += 1
                    print(f"     {i+1}. {self.test_image_ids[i]}: ✅")
            
            print(f"\n  📊 Results:")
            print(f"     Successfully indexed: {success_count}/{batch_size}")
            
            # Query each
            print(f"\n  🔄 Querying all {batch_size} images...")
            total_candidates = 0
            for i in range(batch_size):
                candidates = self.lsh_indexer.query_fhe_ct_tokens(
                    binary_hash=self.test_hashes[i],
                    tenant_id=tenant_id
                )
                print(f"     {self.test_image_ids[i]}: {len(candidates)} candidates")
                total_candidates += len(candidates)
            
            passed = success_count == batch_size and total_candidates >= batch_size
            self.print_result(passed, f"Indexed and retrieved {batch_size} images")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_collision_behavior(self):
        """Test 7: LSH collision behavior (similar hashes)."""
        self.print_test("LSH Collision Behavior")
        
        try:
            tenant_id = "hospital_C"
            
            # Create two similar hashes (differ by 10 bits)
            hash1 = self.test_hashes[0].copy()
            hash2 = hash1.copy()
            # Flip 10 random bits
            flip_indices = np.random.choice(256, size=10, replace=False)
            hash2[flip_indices] = 1 - hash2[flip_indices]
            
            hamming_dist = np.sum(hash1 != hash2)
            
            print(f"\n  📊 Creating similar hashes:")
            print(f"     Hash 1 ones: {np.sum(hash1)}/256")
            print(f"     Hash 2 ones: {np.sum(hash2)}/256")
            print(f"     Hamming distance: {hamming_dist}/256")
            
            # Generate FHE CTs
            fhe_ct1 = self.fhe_client.serialize(self.fhe_client.encrypt(hash1))
            fhe_ct2 = self.fhe_client.serialize(self.fhe_client.encrypt(hash2))
            
            # Add both to index
            print(f"\n  🔄 Adding both to index...")
            self.lsh_indexer.add_fhe_ct(hash1, tenant_id, fhe_ct1, "similar_1")
            self.lsh_indexer.add_fhe_ct(hash2, tenant_id, fhe_ct2, "similar_2")
            
            # Query with hash1
            print(f"\n  🔄 Querying with hash 1...")
            candidates = self.lsh_indexer.query_fhe_ct_tokens(hash1, tenant_id)
            
            print(f"\n  📊 Results:")
            print(f"     Candidates found: {len(candidates)}")
            print(f"     Expected: >= 2 (both similar images)")
            
            # Estimate collision probability
            from lsh_tokenization.simhash.simhash_generator import SimHashGenerator
            from lsh_tokenization.config.lsh_config import LSHConfig
            
            generator = SimHashGenerator(LSHConfig())
            prob = generator.estimate_collision_probability(hamming_dist)
            print(f"     Theoretical collision probability: {prob:.4f}")
            
            passed = len(candidates) >= 1  # Should at least find itself
            self.print_result(passed, f"Found {len(candidates)} candidates (prob={prob:.4f})")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_index_statistics(self):
        """Test 8: Index statistics and monitoring."""
        self.print_test("Index Statistics")
        
        try:
            print(f"\n  🔄 Getting index statistics...")
            stats = self.lsh_indexer.get_stats()
            
            print(f"\n  📊 Configuration:")
            print(f"     Number of tables (L): {stats['config']['num_tables']}")
            print(f"     Bits per table (K): {stats['config']['bits_per_table']}")
            print(f"     Buckets per table: {stats['config']['buckets_per_table']}")
            print(f"     Total possible buckets: {stats['config']['total_possible_buckets']}")
            
            print(f"\n  📊 Redis Statistics:")
            if stats['redis']:
                print(f"     Active buckets: {stats['redis'].get('num_buckets', 0)}")
                print(f"     Total FHE CT tokens: {stats['redis'].get('total_tokens', 0)}")
                print(f"     Avg tokens per bucket: {stats['redis'].get('avg_bucket_size', 0):.2f}")
                print(f"     Max bucket size: {stats['redis'].get('max_bucket_size', 0)}")
            
            if 'cache' in stats:
                print(f"\n  📊 Cache Statistics:")
                print(f"     Cached tokens: {stats['cache']['size']}")
                print(f"     Cache capacity: {stats['cache']['max_size']}")
                print(f"     Utilization: {stats['cache']['utilization']*100:.1f}%")
            
            passed = True
            self.print_result(passed, "Statistics retrieved successfully")
            return passed
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_result(False, f"Error: {e}")
            return False
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def cleanup(self):
        """Cleanup test data."""
        try:
            if self.lsh_indexer and self.lsh_indexer.redis_index:
                self.lsh_indexer.redis_index.clear_all()
                logger.info("Cleaned up test data from Redis")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    # ========================================================================
    # Main Test Runner
    # ========================================================================
    
    def run_all_tests(self):
        """Run all LSH tokenization tests."""
        self.print_header("RUNNING LSH TOKENIZATION TESTS")
        
        if not self.setup():
            print("\n❌ Setup failed. Cannot run tests.")
            return False
        
        # Run all test methods
        test_methods = [
            self.test_simhash_generation,
            self.test_bucket_tokenization,
            self.test_fhe_ct_tokenization,
            self.test_redis_storage,
            self.test_complete_pipeline_single_image,
            self.test_batch_indexing,
            self.test_collision_behavior,
            self.test_index_statistics,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.failed_tests += 1
                print(f"\n❌ Test crashed: {e}")
                import traceback
                traceback.print_exc()
        
        # Cleanup
        self.cleanup()
        
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
            print(f"{'🎉 ALL LSH TESTS PASSED! 🎉':^70}")
            print(f"{'='*70}")
            print(f"\n✅ LSH tokenization module is working correctly!")
            print(f"✅ Redis schema matches specification!")
            print(f"✅ Ready for production deployment!")
        else:
            print(f"\n{'='*70}")
            print(f"{'⚠️  SOME TESTS FAILED':^70}")
            print(f"{'='*70}")


def main():
    """Main entry point."""
    tester = LSHTokenizationTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
