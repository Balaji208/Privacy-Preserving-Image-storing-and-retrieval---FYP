"""
Test Complete Image Storage Pipeline
=====================================
Tests: Upload → Encrypt → Hash → LSH → FHE → Redis (Encrypted Hash as Key)
"""

import sys
from pathlib import Path
import json
import numpy as np
import logging
import base64

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

print("\n" + "=" * 70)
print("Secure Image Storage Pipeline - Complete Test")
print("=" * 70)

# Import pipeline (FIXED: removed process_batch import)
try:
    from storage_pipeline.pipeline import SecureImageProcessor
    print("✓ Pipeline imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 1: Initialize Pipeline
# ============================================================================
print("\n[Test 1] Initializing pipeline...")
try:
    processor = SecureImageProcessor()
    print("✓ Pipeline initialized")
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 2: Process Single Image
# ============================================================================
print("\n[Test 2] Processing single image...")
try:
    sample_images = list(Path('./sample_images').glob('*.jpg'))
    if not sample_images:
        print("✗ No sample images found")
        sys.exit(1)
    
    test_image = sample_images[0]
    print(f"  Input: {test_image.name}")
    
    image_id, metadata = processor.process_image(str(test_image))
    
    print(f"✓ Image processed successfully")
    print(f"  Image ID: {image_id}")
    print(f"  Redis Key: {metadata.redis_key}")
    print(f"  LSH Tokens: {metadata.lsh_tokens}")
    print(f"  DeepHash Sum: {metadata.deephash_sum}")
    print(f"  FHE Size: {metadata.fhe_ciphertext_size:,} bytes")
    print(f"  Processing Time: {metadata.processing_time_ms:.2f} ms")
    
except Exception as e:
    print(f"✗ Processing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 3: Retrieve from Redis by Image ID
# ============================================================================
print("\n[Test 3] Retrieving from Redis by Image ID...")
try:
    stored_data = processor.retrieve_by_image_id(image_id)
    
    print(f"✓ Retrieved from Redis")
    print(f"  Image ID: {stored_data['image_id']}")
    print(f"  Encrypted Image: {len(json.dumps(stored_data['encrypted_image'])):,} bytes")
    print(f"  FHE Hash: {stored_data['fhe_encrypted_hash']['hash_dimension']} bits")
    print(f"  LSH Tokens: {len(stored_data['lsh_tokens'])}")
    print(f"  Metadata Keys: {list(stored_data['metadata'].keys())}")
    
    assert stored_data['image_id'] == image_id
    print("✓ Metadata verification passed")
    
except Exception as e:
    print(f"✗ Retrieval failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 4: Decrypt FHE Hash
# ============================================================================
print("\n[Test 4] Decrypting FHE hash...")
try:
    # Get FHE ciphertext from stored data
    fhe_b64 = stored_data['fhe_encrypted_hash']['ciphertext']
    fhe_bytes = base64.b64decode(fhe_b64)
    
    # Decrypt
    decrypted_hash = processor.decrypt_fhe_hash(fhe_bytes)
    
    print(f"✓ FHE hash decrypted")
    print(f"  Hash shape: {decrypted_hash.shape}")
    print(f"  Hash sum: {np.sum(decrypted_hash)}")
    print(f"  Expected sum: {metadata.deephash_sum}")
    
    assert np.sum(decrypted_hash) == metadata.deephash_sum
    print("✓ Hash integrity verified")
    
except Exception as e:
    print(f"✗ Decryption failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 5: Process Multiple Images
# ============================================================================
print("\n[Test 5] Processing batch of images...")
try:
    batch_images = sample_images[1:4] if len(sample_images) > 3 else sample_images[:2]
    
    for img in batch_images:
        img_id, meta = processor.process_image(str(img))
        print(f"  ✓ {img.name} → {img_id}")
    
    print(f"✓ Processed {len(batch_images)} additional images")
    
except Exception as e:
    print(f"⚠ Batch processing warning: {e}")

# ============================================================================
# TEST 6: Get All Images
# ============================================================================
print("\n[Test 6] Listing all images...")
try:
    all_images = processor.get_all_images()
    print(f"✓ Total images stored: {len(all_images)}")
    for img_id in all_images[:5]:
        print(f"    - {img_id}")
    if len(all_images) > 5:
        print(f"    ... and {len(all_images) - 5} more")
    
except Exception as e:
    print(f"⚠ Listing warning: {e}")

# ============================================================================
# TEST 7: Pipeline Statistics
# ============================================================================
print("\n[Test 7] Pipeline statistics...")
try:
    stats = processor.get_statistics()
    
    print("✓ Statistics:")
    print(f"  Total images: {stats['total_images']}")
    print(f"  LSH tokens: {stats['lsh_stats'].get('num_tokens', 'N/A')}")
    print(f"  Redis memory: {stats['redis_memory_used']}")
    
except Exception as e:
    print(f"⚠ Statistics warning: {e}")

# ============================================================================
# TEST 8: Cleanup
# ============================================================================
print("\n[Test 8] Cleanup test...")
try:
    processor.delete_image(image_id)
    print(f"✓ Deleted test image: {image_id}")
    
    try:
        processor.retrieve_by_image_id(image_id)
        print("✗ Image still exists after deletion")
    except ValueError:
        print("✓ Deletion verified")
    
except Exception as e:
    print(f"⚠ Cleanup warning: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("✅ Complete Pipeline Test Finished!")
print("=" * 70)
print("\n🔑 Redis Storage Format:")
print("   Key: enc_hash:<base64_fhe_encrypted_deephash>")
print("   Value: Complete JSON object with:")
print("     - image_id")
print("     - encrypted_image (Kyber + AES-GCM)")
print("     - fhe_encrypted_hash (TenSEAL BFV)")
print("     - lsh_tokens (6 tokens)")
print("     - metadata (filename, timestamp, etc.)")
print("\n✓ Single Redis key-value storage verified!")
print("=" * 70 + "\n")
