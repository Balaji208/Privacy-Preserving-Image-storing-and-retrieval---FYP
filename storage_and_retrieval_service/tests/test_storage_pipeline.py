"""
Complete Storage Pipeline Test Suite
=====================================

Tests the ENTIRE storage pipeline with FHE_CT embedded in Azure Blob Storage.

Run:
    python tests/test_storage_pipeline.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import numpy as np
import logging
import redis
import time
import json
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class StoragePipelineTester:
    """Comprehensive test suite for storage pipeline."""

    def __init__(self):
        self.pipeline = None
        self.redis_client = None
        self.sample_images = []
        self.stored_data = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def print_header(self, title, char="="):
        width = 70
        print(f"\n{char * width}")
        print(f"{title:^{width}}")
        print(f"{char * width}")

    def print_test_start(self, test_name):
        print(f"\n{'TEST:':<12} {test_name}")
        print(f"{'─' * 70}")

    def print_result(self, passed, message="", details=None):
        status = "✅ PASSED" if passed else "❌ FAILED"
        if passed:
            self.passed += 1
        else:
            self.failed += 1

        print(f"{'STATUS:':<12} {status}")
        if message:
            print(f"{'INFO:':<12} {message}")
        if details:
            print(f"\n{'DETAILS:':<12}")
            for key, value in details.items():
                print(f"  {key:<25} {value}")

    def setup(self):
        """Setup test environment."""
        self.print_header("STORAGE PIPELINE TEST SUITE - SETUP")

        print("\n[1/5] Checking Azure Storage connection...")

        # ✅ TRY MULTIPLE ENVIRONMENT VARIABLE NAMES
        azure_conn = (
            os.getenv("AZURE_STORAGE_CONNECTION_STRING") or
            os.getenv("AZURE_BLOB_STORAGE_CONNECTION_STRING") or
            os.getenv("AZURE_TABLE_STORAGE_CONNECTION_STRING")
        )

        if not azure_conn:
            print("❌ Azure connection string not found in .env")
            print("\n   Expected one of:")
            print("   - AZURE_STORAGE_CONNECTION_STRING")
            print("   - AZURE_BLOB_STORAGE_CONNECTION_STRING")
            print("   - AZURE_TABLE_STORAGE_CONNECTION_STRING")
            print("\n   Current .env variables:")
            for key in os.environ:
                if 'AZURE' in key.upper():
                    print(f"   - {key}")
            return False

        print(f"✅ Azure connection: {azure_conn[:50]}...")

        print("\n[2/5] Checking Redis...")
        try:
            self.redis_client = redis.Redis(host="localhost", port=6379, db=0)
            self.redis_client.ping()
            print("✅ Redis connected")
            keys = self.redis_client.keys("lsh:token:*")
            if keys:
                self.redis_client.delete(*keys)
                print(f"   Cleaned {len(keys)} LSH keys")
        except Exception as e:
            print(f"❌ Redis not running: {e}")
            print("   Start with: redis-server")
            return False

        print("\n[3/5] Checking sample images...")
        sample_dir = Path("sample_images")
        if not sample_dir.exists():
            print(f"❌ {sample_dir} not found")
            print(f"\n   Create directory and add test images:")
            print(f"   mkdir sample_images")
            return False

        for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
            self.sample_images.extend(list(sample_dir.glob(ext)))
        self.sample_images = self.sample_images[:5]

        if not self.sample_images:
            print("❌ No images found in sample_images/")
            print("\n   Add some test images (.jpg, .png, .bmp)")
            return False

        print(f"✅ Found {len(self.sample_images)} images:")
        for i, img in enumerate(self.sample_images, 1):
            size_kb = img.stat().st_size / 1024
            print(f"   {i}. {img.name:<30} ({size_kb:,.1f} KB)")

        print("\n[4/5] Initializing pipeline...")
        try:
            from storage_pipeline import SecureImagePipeline, AzureStorageConfig

            azure_config = AzureStorageConfig(
                connection_string=azure_conn,
                container_name=os.getenv("AZURE_CONTAINER_NAME", "encrypted-images")
            )

            self.pipeline = SecureImagePipeline(
                azure_config=azure_config,
                convnext_model_path="models/convnext_state_dict_only.pt",
                deephash_model_path="models/deephash_state_dict_only.pt",
                redis_host="localhost",
                redis_port=6379,
                tenant_id="test_tenant",
                disable_redis=False
            )
            print("✅ Pipeline initialized")
        except FileNotFoundError as e:
            print(f"❌ Model files not found: {e}")
            print("\n   Required files:")
            print("   - models/convnext_state_dict_only.pt")
            print("   - models/deephash_state_dict_only.pt")
            return False
        except Exception as e:
            print(f"❌ Pipeline init failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("\n[5/5] Verifying components...")
        components = {
            "Encryption Processor": hasattr(self.pipeline, 'encryption_processor'),
            "Feature Processor": hasattr(self.pipeline, 'feature_processor'),
            "Hash Processor": hasattr(self.pipeline, 'hash_processor'),
            "FHE Processor": hasattr(self.pipeline, 'fhe_processor'),
            "Azure Blob Store": hasattr(self.pipeline, 'azure_blob_store'),
            "LSH Indexer": hasattr(self.pipeline, 'lsh_indexer'),
        }

        all_ok = True
        for name, status in components.items():
            symbol = "✅" if status else "❌"
            print(f"   {symbol} {name}")
            if not status:
                all_ok = False

        if not all_ok:
            print("\n❌ Some components missing!")
            return False

        self.print_header("✅ SETUP COMPLETE")
        return True

    def test_01_complete_pipeline(self):
        """Test complete pipeline."""
        self.print_test_start("01 - Complete Pipeline")

        try:
            test_image = self.sample_images[0]
            image_id = f"test_{int(time.time())}"

            print(f"\nProcessing: {test_image.name}")

            start = time.time()
            returned_id, metadata = self.pipeline.process_image(str(test_image), image_id)
            elapsed = time.time() - start

            passed = (
                returned_id == image_id and
                metadata.fhe_ciphertext_size > 0 and
                len(metadata.azure_row_key) > 0
            )

            if passed:
                self.stored_data.append({
                    'image_id': image_id,
                    'blob_name': metadata.azure_row_key
                })

            self.print_result(passed, f"Completed in {elapsed:.2f}s", {
                "Image ID": image_id,
                "FHE CT Size": f"{metadata.fhe_ciphertext_size:,} bytes",
                "DeepHash": f"{metadata.deephash_sum}/256",
                "Blob Name": metadata.azure_row_key[:50] + "..."
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_02_fhe_ct_storage(self):
        """Test FHE_CT is stored in blob."""
        self.print_test_start("02 - FHE_CT Storage Verification")

        if not self.stored_data:
            # Process a new image
            image_id = f"fhe_test_{int(time.time())}"
            _, metadata = self.pipeline.process_image(str(self.sample_images[0]), image_id)
            self.stored_data.append({'image_id': image_id, 'blob_name': metadata.azure_row_key})

        try:
            blob_name = self.stored_data[0]['blob_name']

            print(f"\nRetrieving blob: {blob_name[:50]}...")

            data = self.pipeline.retrieve_by_blob_name(blob_name)

            if not data:
                self.print_result(False, "Blob not found")
                return False

            has_fhe_ct = data.get('fhe_ciphertext') is not None
            has_enc_json = data.get('encryption_json') is not None

            fhe_size = len(data['fhe_ciphertext']) if has_fhe_ct else 0

            passed = has_fhe_ct and has_enc_json and fhe_size > 0

            self.print_result(passed, "FHE_CT found in blob", {
                "Has FHE_CT": "✅" if has_fhe_ct else "❌",
                "FHE_CT Size": f"{fhe_size:,} bytes",
                "Has encryption_json": "✅" if has_enc_json else "❌"
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_03_retrieval_by_blob_name(self):
        """Test retrieval by blob name."""
        self.print_test_start("03 - Retrieval by Blob Name")

        if not self.stored_data:
            self.print_result(False, "No stored data available")
            return False

        try:
            blob_name = self.stored_data[0]['blob_name']

            start = time.time()
            data = self.pipeline.retrieve_by_blob_name(blob_name)
            elapsed = time.time() - start

            passed = data is not None and 'fhe_ciphertext' in data

            self.print_result(passed, f"Retrieved in {elapsed:.3f}s", {
                "Blob Name": blob_name[:50] + "...",
                "Has Data": "✅" if data else "❌"
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False

    def test_04_retrieval_by_image_id(self):
        """Test retrieval by image_id."""
        self.print_test_start("04 - Retrieval by Image ID")

        if not self.stored_data:
            self.print_result(False, "No stored data available")
            return False

        try:
            image_id = self.stored_data[0]['image_id']

            print(f"\nSearching for: {image_id}")
            print("⚠️  This performs blob metadata scan...")

            start = time.time()
            data = self.pipeline.retrieve_by_image_id(image_id)
            elapsed = time.time() - start

            passed = data is not None and data.get('image_id') == image_id

            self.print_result(passed, f"Retrieved in {elapsed:.3f}s", {
                "Image ID": image_id,
                "Found": "✅" if passed else "❌"
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False

    def test_05_redis_lsh_schema(self):
        """Test Redis LSH schema."""
        self.print_test_start("05 - Redis LSH Schema")

        try:
            pattern = "lsh:token:*"
            keys = self.redis_client.keys(pattern)

            if not keys:
                self.print_result(False, "No LSH keys in Redis")
                return False

            sample_key = keys[0].decode('utf-8')
            values = self.redis_client.lrange(keys[0], 0, -1)

            sample_value = values[0].decode('utf-8') if values else ""
            is_hmac = len(sample_value) == 64 and all(c in "0123456789abcdef" for c in sample_value)

            passed = len(keys) > 0 and is_hmac

            self.print_result(passed, "Redis LSH schema verified", {
                "Total LSH Keys": len(keys),
                "Sample Key": sample_key[:50] + "...",
                "Values in Bucket": len(values),
                "HMAC Format": "✅" if is_hmac else "❌"
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False

    def test_06_batch_processing(self):
        """Test batch processing."""
        self.print_test_start("06 - Batch Processing")

        try:
            batch_size = min(3, len(self.sample_images))
            print(f"\nProcessing {batch_size} images...")

            total_time = 0
            success_count = 0

            for i, img in enumerate(self.sample_images[:batch_size], 1):
                try:
                    image_id = f"batch_{i}_{int(time.time())}"
                    start = time.time()
                    _, metadata = self.pipeline.process_image(str(img), image_id)
                    elapsed = time.time() - start
                    total_time += elapsed
                    success_count += 1
                    print(f"  [{i}/{batch_size}] {img.name}: ✅ ({elapsed:.2f}s)")
                except Exception as e:
                    print(f"  [{i}/{batch_size}] {img.name}: ❌ {e}")

            passed = success_count == batch_size

            self.print_result(passed, f"Processed {success_count}/{batch_size}", {
                "Total Time": f"{total_time:.2f}s",
                "Avg Time": f"{total_time/batch_size:.2f}s per image"
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False

    def test_07_statistics(self):
        """Test pipeline statistics."""
        self.print_test_start("07 - Pipeline Statistics")

        try:
            stats = self.pipeline.get_statistics()

            total_blobs = stats.get('total_blobs', 0)

            passed = total_blobs > 0

            self.print_result(passed, "Statistics retrieved", {
                "Tenant ID": stats.get('tenant_id'),
                "Total Blobs": total_blobs,
                "Redis Enabled": not stats.get('disable_redis')
            })

            return passed
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False

    def run_all_tests(self):
        """Run all tests."""
        self.print_header("STORAGE PIPELINE - COMPREHENSIVE TEST SUITE")

        if not self.setup():
            print("\n❌ Setup failed")
            print("\n📋 Troubleshooting:")
            print("   1. Check .env has Azure connection string")
            print("   2. Start Redis: redis-server")
            print("   3. Add test images to sample_images/")
            print("   4. Ensure models/ directory has required .pt files")
            return False

        tests = [
            self.test_01_complete_pipeline,
            self.test_02_fhe_ct_storage,
            self.test_03_retrieval_by_blob_name,
            self.test_04_retrieval_by_image_id,
            self.test_05_redis_lsh_schema,
            self.test_06_batch_processing,
            self.test_07_statistics,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self.failed += 1
                print(f"\n❌ Test crashed: {e}")

        self.print_summary()
        return self.failed == 0

    def print_summary(self):
        """Print summary."""
        self.print_header("TEST SUMMARY")

        total = self.passed + self.failed
        print(f"\n{'Total:':<20} {total}")
        print(f"{'✅ Passed:':<20} {self.passed}")
        print(f"{'❌ Failed:':<20} {self.failed}")

        if self.failed == 0:
            self.print_header("🎉 ALL TESTS PASSED! 🎉")
            print("\n✅ Storage pipeline working correctly!")
            print("✅ FHE_CT storage verified!")
            print("✅ Ready for production!")
        else:
            self.print_header("⚠️  SOME TESTS FAILED")


def main():
    tester = StoragePipelineTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()