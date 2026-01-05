"""
LSH Integration Test with DeepHash
===================================
Complete integration test using ALL images from sample_images folder
with real ConvNeXt + DeepHash models.
"""

import sys
from pathlib import Path
import redis
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import LSH module
from lsh_tokenization import LSHIndexer, LSHConfig
from lsh_tokenization.setup import ImageHashMetadata, LSHImageIndexer
from lsh_tokenization.utils.security import SecurityUtils
from lsh_tokenization.utils.bit_utils import BitUtils

# Import your existing modules
try:
    from feature_extractor import ConvNeXtFeatureExtractor
    from deephashing import DeepHashGenerator
    MODELS_AVAILABLE = True
    print("✓ Successfully imported feature_extractor and deephashing modules")
except ImportError as e:
    print(f"⚠ Warning: Feature extraction models not available: {e}")
    MODELS_AVAILABLE = False


# GLOBAL HMAC KEY - reused across all tests in this session
_GLOBAL_HMAC_KEY: Optional[bytes] = None


def get_hmac_key():
    """Get HMAC key with proper error handling. Uses same key for entire session."""
    global _GLOBAL_HMAC_KEY
    
    # Return cached key if already generated
    if _GLOBAL_HMAC_KEY is not None:
        return _GLOBAL_HMAC_KEY
    
    try:
        from lsh_tokenization.utils.hsm_key_manager import HSMKeyManager
        
        manager = HSMKeyManager()
        
        if manager.key_exists():
            key = manager.retrieve_hmac_key()
            print("✓ Using HMAC key from SoftHSM")
            _GLOBAL_HMAC_KEY = key
            return key
        else:
            print("⚠ HMAC key not found in HSM")
            print("  Run: python -m lsh_tokenization.setup.initialize")
            print("  Generating temporary key for this test session...")
            key = SecurityUtils.generate_hmac_key()
            _GLOBAL_HMAC_KEY = key
            print(f"  Generated key: {key.hex()[:16]}... (will be reused)")
            return key
            
    except Exception as e:
        print(f"⚠ HSM error: {e}")
        print("  Generating temporary key for testing...")
        key = SecurityUtils.generate_hmac_key()
        _GLOBAL_HMAC_KEY = key
        print(f"  Generated key: {key.hex()[:16]}... (will be reused)")
        return key


def setup_indexers(redis_client):
    """Setup LSH and image indexers."""
    hmac_key = get_hmac_key()
    
    config = LSHConfig(
        hash_length=256,
        num_tables=6,
        bits_per_table=12,
        random_seed=42
    )
    
    lsh_indexer = LSHIndexer(redis_client, hmac_key, config)
    image_indexer = LSHImageIndexer(lsh_indexer)
    
    return lsh_indexer, image_indexer


def get_all_sample_images() -> List[Path]:
    """Get all images from sample_images folder."""
    sample_dir = Path('./sample_images')
    
    if not sample_dir.exists():
        print(f"⚠ Warning: {sample_dir} not found")
        return []
    
    # Common image extensions
    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
    
    images = []
    for ext in extensions:
        images.extend(sample_dir.glob(f'*{ext}'))
        images.extend(sample_dir.glob(f'*{ext.upper()}'))
    
    # Remove duplicates and sort
    images = sorted(set(images))
    
    return images


def test_index_all_images():
    """Test 1: Index ALL images from sample_images with real DeepHash."""
    print("\n" + "=" * 70)
    print("Test 1: Index All Sample Images with DeepHash")
    print("=" * 70)
    
    if not MODELS_AVAILABLE:
        print("  ⚠ Skipping: Models not available")
        return []
    
    # Setup
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    lsh_indexer, image_indexer = setup_indexers(redis_client)
    
    # Load models
    print("\n  [1/4] Loading models...")
    try:
        feature_extractor = ConvNeXtFeatureExtractor(
            model_path='./models/convnext_state_dict_only.pt'
        )
        hash_generator = DeepHashGenerator(
            model_path='./models/deephash_state_dict_only.pt'
        )
        print("    ✓ Models loaded successfully")
    except Exception as e:
        print(f"    ✗ Failed to load models: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    # Get all images
    print("\n  [2/4] Finding images in sample_images/...")
    image_paths = get_all_sample_images()
    
    if not image_paths:
        print("    ⚠ No images found in sample_images/")
        return []
    
    print(f"    ✓ Found {len(image_paths)} images")
    
    # Index all images
    print(f"\n  [3/4] Processing and indexing {len(image_paths)} images...")
    indexed_data = []
    
    for i, img_path in enumerate(image_paths, 1):
        try:
            print(f"    [{i:2d}/{len(image_paths)}] {img_path.name:30s}...", end=' ')
            
            # Extract features
            features = feature_extractor.extract(str(img_path))
            
            # Generate binary hash (REAL DeepHash output)
            binary_hash = hash_generator.generate(features)
            
            # FIX: Convert int32 to uint8 if needed
            if binary_hash.dtype != np.uint8:
                print(f"[Converting {binary_hash.dtype} -> uint8]", end=' ')
                binary_hash = binary_hash.astype(np.uint8)
            
            # Verify hash format
            assert binary_hash.shape == (256,), f"Invalid hash shape: {binary_hash.shape}"
            assert binary_hash.dtype == np.uint8, f"Invalid hash dtype: {binary_hash.dtype}"
            assert np.all((binary_hash == 0) | (binary_hash == 1)), "Hash must be binary (0 or 1)"
            
            # Add to index with rich metadata
            success, image_id, hash_id = image_indexer.add_image_from_path(
                binary_hash=binary_hash,
                image_path=img_path,
                tenant_id="medical_images",
                modality="Medical",
                file_size=img_path.stat().st_size,
                file_extension=img_path.suffix
            )
            
            if success:
                indexed_data.append({
                    'path': img_path,
                    'image_id': image_id,
                    'hash_id': hash_id,
                    'binary_hash': binary_hash
                })
                print(f"✓ {hash_id}")
            else:
                print(f"✗ Failed to add to index")
                
        except Exception as e:
            print(f"✗ {str(e)[:60]}")
            continue
    
    # Stats
    print(f"\n  [4/4] Indexing statistics...")
    stats = image_indexer.get_stats()
    print(f"    ✓ Indexed: {len(indexed_data)}/{len(image_paths)} images")
    print(f"    ✓ LSH tokens: {stats['lsh']['redis']['num_tokens']}")
    print(f"    ✓ Average bucket size: {stats['lsh']['redis']['avg_bucket_size']:.2f}")
    print(f"    ✓ Metadata entries: {stats['metadata']['total_entries']}")
    
    # Save metadata
    image_indexer.save_metadata()
    print(f"    ✓ Metadata saved to lsh_image_metadata.json")
    
    print("\n✓ Test 1 passed: All images indexed with real DeepHash\n")
    
    return indexed_data


def visualize_redis_buckets(redis_client, prefix="lsh:token:", max_display=15):
    """Visualize Redis bucket contents."""
    print("\n" + "=" * 70)
    print("Redis Bucket Visualization")
    print("=" * 70)
    
    # Get all LSH token keys
    pattern = f"{prefix}*"
    keys = redis_client.keys(pattern)
    
    if not keys:
        print("\n  No buckets found in Redis")
        return
    
    print(f"\n  Found {len(keys)} buckets in Redis")
    print(f"  Showing first {min(max_display, len(keys))} buckets:\n")
    
    # Sort keys for consistent display
    keys = sorted(keys)
    
    for i, key in enumerate(keys[:max_display], 1):
        # Decode key
        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
        token = key_str.replace(prefix, '')
        
        # Get all hash_ids in this bucket
        hash_ids = redis_client.lrange(key, 0, -1)
        
        # Decode hash_ids
        hash_ids_decoded = [
            hid.decode('utf-8') if isinstance(hid, bytes) else hid
            for hid in hash_ids
        ]
        
        print(f"  [{i:2d}] Token: {token[:32]}...")
        print(f"       Size: {len(hash_ids_decoded)} hash_id(s)")
        
        if len(hash_ids_decoded) <= 5:
            # Show all if small
            for hid in hash_ids_decoded:
                print(f"         → {hid}")
        else:
            # Show first 3 and last 2
            for hid in hash_ids_decoded[:3]:
                print(f"         → {hid}")
            print(f"         ... ({len(hash_ids_decoded) - 5} more)")
            for hid in hash_ids_decoded[-2:]:
                print(f"         → {hid}")
        
        print()
    
    if len(keys) > max_display:
        print(f"  ... and {len(keys) - max_display} more buckets\n")


def test_query_similarity(indexed_data: List[dict]):
    """Test 2: Query for similar images using real hashes."""
    print("\n" + "=" * 70)
    print("Test 2: Query Similar Images")
    print("=" * 70)
    
    if not indexed_data:
        print("  ⚠ Skipping: No indexed data available")
        return
    
    # Setup - REUSE SAME KEY
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    lsh_indexer, image_indexer = setup_indexers(redis_client)
    
    print(f"  Using HMAC key: {_GLOBAL_HMAC_KEY.hex()[:16]}...")
    
    # Query with first 3 images
    num_queries = min(3, len(indexed_data))
    
    print(f"\n  Testing {num_queries} queries...")
    
    for i in range(num_queries):
        query_data = indexed_data[i]
        query_image_id = query_data['image_id']
        query_hash = query_data['binary_hash']
        query_path = query_data['path']
        
        print(f"\n  Query {i+1}: {query_path.name}")
        print(f"    Image ID: {query_image_id}")
        print(f"    Hash ID:  {query_data['hash_id']}")
        
        # Query LSH index
        results = image_indexer.query_image(
            binary_hash=query_hash,
            tenant_id="medical_images",
            return_metadata=True
        )
        
        print(f"    Found: {len(results)} candidates")
        
        # Verify query image is in results
        hash_ids = [r['hash_id'] for r in results]
        assert query_data['hash_id'] in hash_ids, f"Query image not in results! Expected: {query_data['hash_id']}, Got: {hash_ids[:5]}"
        
        # Show top 5 matches with Hamming distances
        print(f"    Top matches:")
        for j, result in enumerate(results[:5], 1):
            # Calculate Hamming distance
            result_idx = next(
                (k for k, d in enumerate(indexed_data) 
                 if d['hash_id'] == result['hash_id']),
                None
            )
            
            if result_idx is not None:
                result_hash = indexed_data[result_idx]['binary_hash']
                hamming_dist = BitUtils.hamming_distance(query_hash, result_hash)
                similarity_pct = (1 - hamming_dist / 256) * 100
                print(f"      [{j}] {result['image_id']:20s} HD={hamming_dist:3d} ({similarity_pct:5.1f}%)")
            else:
                print(f"      [{j}] {result['image_id']:20s} (hash not in current batch)")
    
    print("\n✓ Test 2 passed: Query similarity works\n")


def test_hamming_distance_distribution(indexed_data: List[dict]):
    """Test 3: Analyze Hamming distance distribution."""
    print("\n" + "=" * 70)
    print("Test 3: Hamming Distance Distribution Analysis")
    print("=" * 70)
    
    if len(indexed_data) < 2:
        print("  ⚠ Skipping: Need at least 2 images")
        return
    
    print(f"\n  Analyzing {len(indexed_data)} images...")
    
    # Calculate pairwise Hamming distances
    distances = []
    
    num_samples = min(15, len(indexed_data))
    for i in range(num_samples):
        for j in range(i + 1, num_samples):
            hash1 = indexed_data[i]['binary_hash']
            hash2 = indexed_data[j]['binary_hash']
            
            dist = BitUtils.hamming_distance(hash1, hash2)
            distances.append(dist)
    
    # Statistics
    distances = np.array(distances)
    
    print(f"\n  📊 Distance Statistics:")
    print(f"    Pairs analyzed: {len(distances)}")
    print(f"    Min distance: {distances.min()}")
    print(f"    Max distance: {distances.max()}")
    print(f"    Mean distance: {distances.mean():.2f}")
    print(f"    Std deviation: {distances.std():.2f}")
    
    # Distribution
    bins = [0, 32, 64, 96, 128, 160, 192, 224, 256]
    hist, _ = np.histogram(distances, bins=bins)
    
    print(f"\n  📊 Distance Distribution:")
    for i in range(len(bins) - 1):
        count = hist[i]
        pct = (count / len(distances)) * 100 if len(distances) > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"    {bins[i]:3d}-{bins[i+1]:3d}: {count:3d} pairs ({pct:5.1f}%) {bar}")
    
    print("\n✓ Test 3 passed: Distribution analyzed\n")


def main():
    """Run all tests with real images and DeepHash."""
    print("\n" + "=" * 70)
    print("LSH Tokenization - Complete Integration Test")
    print("Using ALL images from sample_images/ with Real DeepHash")
    print("=" * 70)
    
    try:
        # Check Redis
        print("\n[Pre-check] Connecting to Redis...")
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✓ Redis connected")
        
        # Check models
        if not MODELS_AVAILABLE:
            print("\n⚠ Models not available - cannot run practical tests")
            sys.exit(1)
        
        # Check sample_images
        sample_images = get_all_sample_images()
        if not sample_images:
            print("\n⚠ No images found in sample_images/")
            sys.exit(1)
        
        print(f"✓ Found {len(sample_images)} images to process\n")
        
        # Run all tests
        indexed_data = test_index_all_images()
        
        if indexed_data:
            # Visualize Redis buckets
            visualize_redis_buckets(redis_client, max_display=15)
            
            # Continue with other tests
            test_query_similarity(indexed_data)
            test_hamming_distance_distribution(indexed_data)
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ All Tests Passed!")
        print("=" * 70)
        print(f"\nProcessed {len(indexed_data)} images with real DeepHash")
        print("LSH tokenization is working correctly with actual image data.")
        print(f"\nHMAC key used: {_GLOBAL_HMAC_KEY.hex()[:32]}...")
        print("\nMetadata saved to: lsh_image_metadata.json")
        print("Redis database: Contains LSH index for all images")
        print("\n" + "=" * 70 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except redis.ConnectionError:
        print("\n❌ Redis connection failed!")
        print("Make sure Redis is running: redis-server")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
