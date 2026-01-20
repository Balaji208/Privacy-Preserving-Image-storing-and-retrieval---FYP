"""
Complete FHE + DeepHash Integration Test
=========================================
Tests the full pipeline: DeepHash → FHE Encryption → Storage → Decryption

NOTE: All tests use SERVER MODE (load from HSM) to avoid .env dependency.
In production, clients would use .env for encryption-only operations.
"""

import numpy as np
import sys
from pathlib import Path

# Add parent directory to path (to import fhe_encryption)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fhe_encryption import BFVPipeline


def test_deephash_to_fhe():
    """Test: DeepHash output → FHE encryption → Decryption."""
    print("\n" + "="*70)
    print("TEST 1: DeepHash → FHE Encryption (SERVER MODE)")
    print("="*70)
    
    # Simulate DeepHash output (256-bit binary hash)
    print("\n[1.1] Simulating DeepHash output...")
    deephash_output = np.random.randint(0, 2, 256, dtype=np.uint8)
    print(f"       DeepHash: {deephash_output[:16]}... ({len(deephash_output)} bits)")
    
    # Initialize FHE pipeline (SERVER-SIDE, has both encrypt/decrypt)
    print("\n[1.2] Initializing server-side FHE pipeline...")
    pipeline = BFVPipeline(load_secret_key=True)  # ✅ Loads from HSM
    
    info = pipeline.get_info()
    print(f"       Mode: {info['mode']}")
    print(f"       Backend: {info['backend']}")
    print(f"       Key storage: {info['key_storage']}")
    
    # Encrypt DeepHash
    print("\n[1.3] Encrypting DeepHash output...")
    ciphertext = pipeline.encrypt(deephash_output)
    
    # Get size
    size_info = pipeline.get_ciphertext_size(ciphertext)
    print(f"       ✓ Encrypted ciphertext: {size_info['total_bytes']:,} bytes")
    print(f"       ✓ Scheme: {size_info['scheme']}")
    
    # Serialize for storage/transmission
    print("\n[1.4] Serializing ciphertext...")
    ct_bytes = pipeline.serialize(ciphertext)
    print(f"       ✓ Serialized: {len(ct_bytes):,} bytes")
    
    # Deserialize and decrypt
    print("\n[1.5] Decryption...")
    ct_reconstructed = pipeline.deserialize(ct_bytes)
    
    # Decrypt
    decrypted_hash = pipeline.decrypt(ct_reconstructed, hash_length=256)
    print(f"       Decrypted: {decrypted_hash[:16]}...")
    
    # Verify
    assert np.array_equal(deephash_output, decrypted_hash)
    print("\n✅ DeepHash → FHE → Decryption: SUCCESS!")
    
    return ciphertext, ct_bytes


def test_encrypted_hamming_distance():
    """Test: Encrypted Hamming distance computation."""
    print("\n" + "="*70)
    print("TEST 2: Encrypted Hamming Distance (SERVER MODE)")
    print("="*70)
    
    # Two DeepHash outputs (simulated)
    hash1 = np.array([1, 0, 1, 1, 0, 0, 1, 0] * 32, dtype=np.uint8)  # 256 bits
    hash2 = np.array([1, 1, 0, 1, 0, 1, 0, 0] * 32, dtype=np.uint8)  # 256 bits
    
    print(f"\n[2.1] Hash 1: {hash1[:16]}...")
    print(f"       Hash 2: {hash2[:16]}...")
    
    # Compute expected Hamming distance
    expected_hd = np.sum((hash1 + hash2) % 2)
    print(f"       Expected Hamming distance: {expected_hd}")
    
    # Initialize server pipeline (loads from HSM)
    print("\n[2.2] Initializing server pipeline...")
    pipeline = BFVPipeline(load_secret_key=True)  # ✅ Loads from HSM
    print("       ✓ Pipeline initialized from HSM")
    
    # Encrypt both hashes
    print("\n[2.3] Encrypting both hashes...")
    ctxt1 = pipeline.encrypt(hash1)
    ctxt2 = pipeline.encrypt(hash2)
    print("       ✓ Both hashes encrypted")
    
    # Compute encrypted Hamming distance (XOR)
    print("\n[2.4] Computing encrypted Hamming distance...")
    ctxt_xor = pipeline.hamming_distance(ctxt1, ctxt2, hash_length=256)
    print("       ✓ Encrypted XOR computed")
    
    # Decrypt result
    print("\n[2.5] Decrypting result...")
    decrypted_xor = pipeline.decrypt(ctxt_xor, hash_length=256)
    computed_hd = np.sum(decrypted_xor)
    
    print(f"       Decrypted Hamming distance: {computed_hd}")
    print(f"       Expected: {expected_hd}")
    
    assert computed_hd == expected_hd
    print("\n✅ Encrypted Hamming Distance: SUCCESS!")


def test_batch_encryption():
    """Test: Batch encryption of multiple DeepHash outputs."""
    print("\n" + "="*70)
    print("TEST 3: Batch Encryption (SERVER MODE)")
    print("="*70)
    
    # Simulate 5 DeepHash outputs
    print("\n[3.1] Generating 5 DeepHash outputs...")
    deephashes = [
        np.random.randint(0, 2, 256, dtype=np.uint8)
        for _ in range(5)
    ]
    print(f"       Generated {len(deephashes)} hashes")
    
    # Initialize server pipeline
    print("\n[3.2] Initializing server pipeline...")
    pipeline = BFVPipeline(load_secret_key=True)  # ✅ Loads from HSM
    print("       ✓ Pipeline initialized from HSM")
    
    # Batch encrypt
    print("\n[3.3] Batch encrypting...")
    ciphertexts = pipeline.encrypt_batch(deephashes)
    print(f"       ✓ Encrypted {len(ciphertexts)} ciphertexts")
    
    # Batch decrypt
    print("\n[3.4] Batch decrypting...")
    decrypted_hashes = pipeline.decrypt_batch(ciphertexts, hash_length=256)
    print(f"       ✓ Decrypted {len(decrypted_hashes)} hashes")
    
    # Verify all
    print("\n[3.5] Verifying all hashes...")
    for i, (original, decrypted) in enumerate(zip(deephashes, decrypted_hashes)):
        assert np.array_equal(original, decrypted)
        print(f"       ✓ Hash {i+1} verified")
    
    print("\n✅ Batch Encryption: SUCCESS!")


def test_ciphertext_storage():
    """Test: Serialize/deserialize for database storage."""
    print("\n" + "="*70)
    print("TEST 4: Ciphertext Storage Simulation (SERVER MODE)")
    print("="*70)
    
    deephash = np.random.randint(0, 2, 256, dtype=np.uint8)
    
    # Initialize server pipeline
    print("\n[4.1] Initializing server pipeline...")
    pipeline = BFVPipeline(load_secret_key=True)  # ✅ Loads from HSM
    print("       ✓ Pipeline initialized from HSM")
    
    # Encrypt
    print("\n[4.2] Encrypting DeepHash...")
    ciphertext = pipeline.encrypt(deephash)
    
    # Serialize for storage
    print("\n[4.3] Serializing for database storage...")
    ct_bytes = pipeline.serialize(ciphertext)
    print(f"       Size: {len(ct_bytes):,} bytes")
    
    # Simulate storage (convert to hex for SQL)
    ct_hex = ct_bytes.hex()
    print(f"       Hex length: {len(ct_hex)} chars")
    
    # Retrieve from database
    print("\n[4.4] Retrieving from database...")
    ct_retrieved = bytes.fromhex(ct_hex)
    
    ct_deserialized = pipeline.deserialize(ct_retrieved)
    
    decrypted = pipeline.decrypt(ct_deserialized, hash_length=256)
    
    assert np.array_equal(deephash, decrypted)
    print("       ✓ Retrieved and decrypted successfully")
    
    print("\n✅ Ciphertext Storage: SUCCESS!")


def test_multiple_pipelines():
    """Test: Simulate client encrypts, server decrypts (both using HSM)."""
    print("\n" + "="*70)
    print("TEST 5: Client-Server Simulation (BOTH USE HSM)")
    print("="*70)
    
    # Simulate DeepHash
    deephash = np.random.randint(0, 2, 256, dtype=np.uint8)
    print(f"\n[5.1] Original hash: {deephash[:16]}...")
    
    # Client pipeline (in real scenario, would use .env)
    print("\n[5.2] Client encrypts (using HSM for testing)...")
    client_pipeline = BFVPipeline(load_secret_key=True)  # For testing
    ciphertext = client_pipeline.encrypt(deephash)
    ct_bytes = client_pipeline.serialize(ciphertext)
    print(f"       ✓ Encrypted: {len(ct_bytes):,} bytes")
    
    # Server pipeline
    print("\n[5.3] Server decrypts (using HSM)...")
    server_pipeline = BFVPipeline(load_secret_key=True)
    ct_reconstructed = server_pipeline.deserialize(ct_bytes)
    decrypted = server_pipeline.decrypt(ct_reconstructed, hash_length=256)
    
    print(f"       Decrypted: {decrypted[:16]}...")
    
    assert np.array_equal(deephash, decrypted)
    print("\n✅ Client-Server Simulation: SUCCESS!")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("FHE + DEEPHASH INTEGRATION TESTS (HSM ONLY)")
    print("="*70)
    print("\n⚠️  NOTE: All tests use SERVER MODE (load_secret_key=True)")
    print("   In production:")
    print("   • Clients use .env (TENSEAL_PUBLIC_CONTEXT_BASE64)")
    print("   • Server uses HSM (TENSEAL_BFV_CONTEXT)")
    print("="*70)
    
    try:
        test_deephash_to_fhe()
        test_encrypted_hamming_distance()
        test_batch_encryption()
        test_ciphertext_storage()
        test_multiple_pipelines()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\n💡 Your FHE module is ready for:")
        print("   • Encrypting DeepHash outputs ✓")
        print("   • Encrypted Hamming distance computation ✓")
        print("   • Batch operations ✓")
        print("   • Database storage ✓")
        print("   • Client-server architecture ✓")
        print("\n🔑 Key Management:")
        print("   • Server keys: Loaded from SoftHSM ✓")
        print("   • Client keys: Use .env in production")
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
