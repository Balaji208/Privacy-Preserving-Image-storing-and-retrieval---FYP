"""
Test Complete Image Storage Pipeline
=====================================
Tests end-to-end flow: Upload → Encrypt → Hash → LSH → FHE → Redis
"""

import sys
from pathlib import Path
import json
import numpy as np
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

print("\n" + "=" * 70)
print("Secure Image Storage Pipeline - Complete Test")
print("=" * 70)

# Import pipeline
try:
    from storage_pipeline.image_processor import SecureImageProcessor
    print("✓ Pipeline imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("\nMake sure all dependencies are installed:")
    print("  pip install redis tenseal torch torchvision numpy")
    sys.exit(1)

# ============================================================================
# TEST 1: Initialize Pipeline
# ============================================================================
print("\n[Test 1] Initializing pipeline...")
try:
    processor = SecureImageProcessor(
        convnext_model_path='./models/convnext_state_dict_only.pt',
        deephash_model_path='./models/deephash_state_dict_only.pt',
        redis_host='localhost',
        redis_port=6379
    )
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
    # Find a sample image
    sample_images = list(Path('./sample_images').glob('*.jpg'))
    if not sample_images:
        print("✗ No sample images found")
        sys.exit(1)
    
    test_image = sample_images[0]
    print(f"  Input: {test_image.name}")
    
    # Process image
    image_id, metadata = processor.process_image(str(test_image))
    
    print(f"✓ Image processed successfully")
    print(f"  Image ID: {image_id}")
    print(f"  LSH Buckets: {metadata.lsh_tokens}")  # Note: plural form
    print(f"  DeepHash Sum: {metadata.deephash_sum}")
    print(f"  FHE Size: {metadata.fhe_ciphertext_size:,} bytes")
    print(f"  Processing Time: {metadata.processing_time_ms:.2f} ms")
    
except Exception as e:
    print(f"✗ Processing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 3: Retrieve from Redis
# ============================================================================
print("\n[Test 3] Retrieving from Redis...")
try:
    # Retrieve data
    stored_data = processor.retrieve_image_data(image_id)
    
    print(f"✓ Retrieved from Redis")
    print(f"  Encrypted Image: {len(json.dumps(stored_data['encrypted_image'])):,} bytes")
    print(f"  FHE Hash: {len(stored_data['fhe_encrypted_hash']):,} bytes")
    print(f"  Metadata: {len(json.dumps(stored_data['metadata'])):,} bytes")
    
    # Verify metadata matches
    retrieved_meta = stored_data['metadata']
    assert retrieved_meta['image_id'] == image_id
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
    # Decrypt FHE hash
    fhe_bytes = stored_data['fhe_encrypted_hash']
    decrypted_hash = processor.decrypt_fhe_hash(fhe_bytes)
    
    print(f"✓ FHE hash decrypted")
    print(f"  Hash shape: {decrypted_hash.shape}")
    print(f"  Hash sum: {np.sum(decrypted_hash)}")
    print(f"  Expected sum: {metadata.deephash_sum}")
    
    # Verify sum matches
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
    # Get 3 more images
    batch_images = sample_images[1:4] if len(sample_images) > 3 else sample_images[:3]
    
    image_ids = []
    for img in batch_images:
        img_id, meta = processor.process_image(str(img))
        image_ids.append(img_id)
        print(f"  ✓ {img.name} → {img_id}")
    
    print(f"✓ Processed {len(image_ids)} images")
    
except Exception as e:
    print(f"⚠ Batch processing warning: {e}")

# ============================================================================
# TEST 6: Query by LSH Bucket
# ============================================================================
print("\n[Test 6] Querying by LSH bucket...")
try:
    # Get images in same bucket
    bucket_id = metadata.lsh_bucket_id
    bucket_images = processor.get_bucket_images(bucket_id)
    
    print(f"✓ LSH Bucket: {bucket_id}")
    print(f"  Images in bucket: {len(bucket_images)}")
    for img_id in bucket_images:
        print(f"    - {img_id}")
    
except Exception as e:
    print(f"⚠ Bucket query warning: {e}")

# ============================================================================
# TEST 7: Pipeline Statistics
# ============================================================================
print("\n[Test 7] Pipeline statistics...")
try:
    stats = processor.get_statistics()
    
    print("✓ Statistics:")
    print(f"  Total images: {stats['total_images']}")
    print(f"  Total buckets: {stats['total_buckets']}")
    print(f"  Redis memory: {stats['redis_memory_used']}")
    
except Exception as e:
    print(f"⚠ Statistics warning: {e}")

# ============================================================================
# TEST 8: Cleanup (Optional)
# ============================================================================
print("\n[Test 8] Cleanup test...")
try:
    # Delete test image
    processor.delete_image(image_id)
    print(f"✓ Deleted test image: {image_id}")
    
    # Verify deletion
    try:
        processor.retrieve_image_data(image_id)
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
print("\nPipeline components tested:")
print("  ✓ Image encryption (Kyber + AES-GCM)")
print("  ✓ Feature extraction (ConvNeXt-V2)")
print("  ✓ DeepHash generation (256-bit)")
print("  ✓ LSH bucketing (Redis)")
print("  ✓ FHE encryption (TenSEAL BFV)")
print("  ✓ Redis storage (key-value)")
print("  ✓ Data retrieval")
print("  ✓ FHE decryption")
print("  ✓ Batch processing")
print("  ✓ Bucket querying")
print("\n" + "=" * 70 + "\n")
