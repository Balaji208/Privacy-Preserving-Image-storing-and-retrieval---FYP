"""
Complete System Key Initialization with TenSEAL
================================================

This script generates and stores ALL system-wide cryptographic keys:

1. Kyber-768 Keypair (PQC) - Image Encryption
   - Secret key → HSM
   - Public key → Filesystem

2. LSH HMAC Key - Similarity Search
   - 32 bytes → HSM

3. BFV Keys (Homomorphic Encryption) - Encrypted Search
   - TenSEAL Context → HSM (contains all keys)
   - Public Context → .bin file (for client encryption)

Run this ONCE during system deployment.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hsm.hsm_manager import get_hsm_manager
from hsm.key_store import KeyStore
from image_encryption.crypto.kyber_kem import KyberKEM
from image_encryption.config.kyber_config import KYBER_PUBLIC_KEY_FILE
from pkcs11 import Attribute
import os
import base64

def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(title.center(70))
    print("=" * 70)

def print_step(step_num: int, title: str):
    """Print step header."""
    print(f"\n[{step_num}] {title}")
    print("-" * 70)

def clear_all_hsm_keys():
    """Clear all existing keys from HSM."""
    print_step(1, "Clearing Existing Keys from HSM")

    hsm = get_hsm_manager()
    deleted_count = 0

    for obj in hsm.session.get_objects():
        try:
            label = obj[Attribute.LABEL].decode('utf-8', errors='ignore')
        except:
            label = "(no label)"

        obj.destroy()
        deleted_count += 1
        print(f"   ✓ Deleted: {label}")

    if deleted_count > 0:
        print(f"   ✓ Cleared {deleted_count} key(s)")
    else:
        print("   ℹ No existing keys found")

def generate_kyber_keypair():
    """Generate system-wide Kyber-768 keypair for image encryption."""
    print_step(2, "Generating Kyber-768 Keypair (PQC Image Encryption)")

    print("   Generating ML-KEM-768 keypair...")
    keys = KyberKEM.generate_keypair()

    print(f"   ✓ Public key: {len(keys['public_key'])} bytes")
    print(f"   ✓ Secret key: {len(keys['secret_key'])} bytes")
    print(f"   Purpose: Post-quantum secure image encryption")

    return keys

def store_kyber_keys(keys: dict):
    """Store Kyber keys in HSM and filesystem."""
    print_step(3, "Storing Kyber Keys")

    # Store secret key in HSM
    print("   [3.1] Storing secret key in HSM...")
    key_store = KeyStore()
    key_store.store_kyber_secret_key(keys["secret_key"])
    print(f"   ✓ Stored with label: KYBER_SECRET_KEY")

    # Save public key to filesystem
    print("   [3.2] Saving public key to filesystem...")
    pub_key_path = Path(KYBER_PUBLIC_KEY_FILE)
    pub_key_path.parent.mkdir(parents=True, exist_ok=True)

    with open(pub_key_path, "wb") as f:
        f.write(keys["public_key"])

    print(f"   ✓ Saved to: {pub_key_path}")
    print(f"   ✓ Size: {len(keys['public_key'])} bytes")

def generate_lsh_hmac_key():
    """Generate LSH HMAC key for similarity search."""
    print_step(4, "Generating LSH HMAC Key (Similarity Search)")

    hsm = get_hsm_manager()

    print("   Generating 256-bit HMAC key...")
    lsh_key = os.urandom(32)

    hsm.store_secret_test("LSH_HMAC_KEY", lsh_key)

    print(f"   ✓ Stored in HSM: LSH_HMAC_KEY (32 bytes)")
    print(f"   ✓ Preview: {lsh_key[:8].hex()}...")
    print(f"   Purpose: Secure LSH token generation")

def generate_tenseal_bfv_keys():
    """Generate BFV keys using TenSEAL (NO Pyfhel dependency)."""
    print_step(5, "Generating BFV Keys with TenSEAL")

    try:
        import tenseal as ts
    except ImportError:
        print("   ✗ TenSEAL not installed")
        print("   Install: pip install tenseal")
        return None

    print("   [5.1] Creating TenSEAL BFV context...")

    # BFV parameters (128-bit security)
    poly_modulus_degree = 8192
    plain_modulus = 1032193  # Prime for batching

    print(f"   Polynomial degree: {poly_modulus_degree}")
    print(f"   Plaintext modulus: {plain_modulus}")
    print(f"   Security level: 128-bit")

    # Create BFV context
    context = ts.context(
        ts.SCHEME_TYPE.BFV,
        poly_modulus_degree=poly_modulus_degree,
        plain_modulus=plain_modulus
    )

    print("   [5.2] Generating cryptographic keys...")

    # Generate Galois keys (for rotations/Hamming distance)
    context.generate_galois_keys()

    print("   ✓ Key generation complete")
    print("   ✓ Public key: Generated")
    print("   ✓ Secret key: Generated")
    print("   ✓ Galois keys: Generated")

    # Serialize full context (with secret key)
    context_full = context.serialize(
        save_public_key=True,
        save_secret_key=True,
        save_galois_keys=True,
        save_relin_keys=False  # Not used in our implementation
    )

    # Create public-only context (for client-side encryption)
    context_public = context.copy()
    context_public.make_context_public()
    context_public_bytes = context_public.serialize(
        save_public_key=True,
        save_secret_key=False,  # No secret key
        save_galois_keys=True,
        save_relin_keys=False
    )

    print(f"   ✓ Full context: {len(context_full):,} bytes (with secret key)")
    print(f"   ✓ Public context: {len(context_public_bytes):,} bytes (no secret)")
    print(f"   Purpose: Encrypted similarity search operations")

    return {
        'full_context': context_full,
        'public_context': context_public_bytes,
        'params': {
            'poly_modulus_degree': poly_modulus_degree,
            'plain_modulus': plain_modulus,
            'security_level': 128
        }
    }

def store_tenseal_context(tenseal_keys: dict):
    """Store TenSEAL context in HSM."""
    if tenseal_keys is None:
        return

    print_step(6, "Storing TenSEAL Context in HSM")

    hsm = get_hsm_manager()

    # Store full context (with secret key) in HSM
    print("   [6.1] Storing full context in HSM...")
    hsm.store_secret_test("TENSEAL_BFV_CONTEXT", tenseal_keys['full_context'])

    print(f"   ✓ Stored: {len(tenseal_keys['full_context']):,} bytes")
    print(f"   ✓ Label: TENSEAL_BFV_CONTEXT")
    print(f"   ✓ Contains: Public + Secret + Galois keys")

def store_public_context_file(tenseal_keys: dict):
    """Store public context as .bin file for client-side encryption."""
    if tenseal_keys is None:
        return

    print_step(7, "Storing Public Context as .bin File")

    # Create keys directory
    keys_dir = project_root / "bfv_keys"
    keys_dir.mkdir(exist_ok=True)

    public_context_file = keys_dir / "bfv_context_public.bin"

    print(f"   [7.1] Writing public context to file...")
    print(f"   Target: {public_context_file}")
    print(f"   Size: {len(tenseal_keys['public_context']):,} bytes")

    # Write binary file
    with open(public_context_file, 'wb') as f:
        f.write(tenseal_keys['public_context'])

    file_size = public_context_file.stat().st_size

    print(f"   ✓ Saved to: {public_context_file}")
    print(f"   ✓ File size: {file_size:,} bytes (~{file_size // 1024} KB)")
    print(f"   ✓ Contains: Public key + Galois keys (no secret key)")
    print(f"   ✓ Safe to deploy on untrusted servers")

    # Also save parameters as JSON
    import json
    params_file = keys_dir / "bfv_params.json"
    with open(params_file, 'w') as f:
        json.dump(tenseal_keys['params'], f, indent=2)

    print(f"   ✓ Saved parameters: {params_file}")

def verify_all_keys():
    """Verify all keys are stored correctly."""
    print_step(8, "Verifying All Keys")

    hsm = get_hsm_manager()
    key_store = KeyStore()
    verification_results = []

    # Verify Kyber secret key
    print("   [8.1] Verifying Kyber secret key...")
    try:
        kyber_sk = key_store.load_kyber_secret_key()
        assert len(kyber_sk) == 2400, f"Invalid size: {len(kyber_sk)}"
        print(f"   ✓ KYBER_SECRET_KEY: {len(kyber_sk)} bytes")
        verification_results.append(("Kyber Secret Key (HSM)", True, len(kyber_sk)))
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        verification_results.append(("Kyber Secret Key (HSM)", False, str(e)))

    # Verify Kyber public key file
    print("   [8.2] Verifying Kyber public key file...")
    pub_key_path = Path(KYBER_PUBLIC_KEY_FILE)
    if pub_key_path.exists():
        with open(pub_key_path, "rb") as f:
            pub_key = f.read()
        assert len(pub_key) == 1184, f"Invalid size: {len(pub_key)}"
        print(f"   ✓ Kyber public key: {len(pub_key)} bytes")
        verification_results.append(("Kyber Public Key (File)", True, len(pub_key)))
    else:
        print(f"   ✗ File not found: {pub_key_path}")
        verification_results.append(("Kyber Public Key (File)", False, "Not found"))

    # Verify LSH HMAC key
    print("   [8.3] Verifying LSH HMAC key...")
    try:
        lsh_key = hsm.retrieve_secret("LSH_HMAC_KEY")
        assert len(lsh_key) == 32, f"Invalid size: {len(lsh_key)}"
        print(f"   ✓ LSH_HMAC_KEY: {len(lsh_key)} bytes")
        verification_results.append(("LSH HMAC Key (HSM)", True, len(lsh_key)))
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        verification_results.append(("LSH HMAC Key (HSM)", False, str(e)))

    # Verify TenSEAL context in HSM
    print("   [8.4] Verifying TenSEAL context in HSM...")
    try:
        context_bytes = hsm.retrieve_secret("TENSEAL_BFV_CONTEXT")
        print(f"   ✓ TENSEAL_BFV_CONTEXT: {len(context_bytes):,} bytes")
        verification_results.append(("TenSEAL Context (HSM)", True, len(context_bytes)))
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        verification_results.append(("TenSEAL Context (HSM)", False, str(e)))

    # Verify TenSEAL public context file
    print("   [8.5] Verifying TenSEAL public context file...")
    public_context_file = project_root / "bfv_keys" / "bfv_context_public.bin"
    if public_context_file.exists():
        file_size = public_context_file.stat().st_size
        print(f"   ✓ Public context file: {file_size:,} bytes")
        verification_results.append(("TenSEAL Public Context (File)", True, f"{file_size:,} bytes"))
    else:
        print(f"   ✗ File not found: {public_context_file}")
        verification_results.append(("TenSEAL Public Context (File)", False, "Not found"))

    return verification_results

def display_final_inventory():
    """Display complete HSM key inventory."""
    print_step(9, "Final HSM Key Inventory")

    hsm = get_hsm_manager()
    hsm.list_all_keys()

def print_summary(verification_results: list):
    """Print final summary."""
    print_header("INITIALIZATION SUMMARY")

    success_count = sum(1 for _, success, _ in verification_results if success)
    total_count = len(verification_results)

    print("\n📊 Key Storage Status:\n")

    for key_name, success, info in verification_results:
        status = "✓" if success else "✗"
        if success:
            if isinstance(info, int):
                print(f"   {status} {key_name:<35} │ {info:>15,} bytes")
            else:
                print(f"   {status} {key_name:<35} │ {info:>15}")
        else:
            print(f"   {status} {key_name:<35} │ {info}")

    print(f"\n{'=' * 70}")
    print(f"Status: {success_count}/{total_count} keys initialized successfully")
    print(f"{'=' * 70}\n")

    if success_count == total_count:
        print("✅ ALL SYSTEM KEYS INITIALIZED SUCCESSFULLY")
        print("\n💡 Your system is ready for:")
        print("   • Post-quantum secure image encryption (Kyber)")
        print("   • Secure similarity search (LSH HMAC)")
        print("   • Encrypted similarity search (TenSEAL BFV)")
        print("\n🔑 Key Storage Summary:")
        print("   • Kyber secret key → HSM")
        print("   • LSH HMAC key → HSM")
        print("   • TenSEAL full context (with secret) → HSM")
        print("   • TenSEAL public context → bfv_keys/bfv_context_public.bin")
        print(f"\n{'=' * 70}\n")
        return True
    else:
        print("⚠️ SOME KEYS FAILED TO INITIALIZE")
        print("\nPlease review errors above and re-run if needed.")
        print(f"{'=' * 70}\n")
        return False

def main():
    """Main initialization workflow."""
    print_header("SYSTEM-WIDE KEY INITIALIZATION (TenSEAL)")

    print("\n⚠️ WARNING: This will DELETE all existing keys in HSM!")
    print("   This includes:")
    print("   • Kyber keypair (image encryption)")
    print("   • LSH HMAC key (similarity search)")
    print("   • Old BFV/Pyfhel keys (if any)")
    print("   • TenSEAL BFV context")
    print("\n ✨ New: Stores public context as .bin file (no .env limit)")
    print("\n Press Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\n❌ Aborted by user\n")
        return

    try:
        # Step 1: Clear existing keys
        clear_all_hsm_keys()

        # Step 2-3: Kyber keys
        kyber_keys = generate_kyber_keypair()
        store_kyber_keys(kyber_keys)

        # Step 4: LSH HMAC key
        generate_lsh_hmac_key()

        # Step 5-7: TenSEAL BFV keys
        tenseal_keys = generate_tenseal_bfv_keys()
        store_tenseal_context(tenseal_keys)
        store_public_context_file(tenseal_keys)  # Changed: saves to .bin file

        # Step 8: Verify
        verification_results = verify_all_keys()

        # Step 9: Display inventory
        display_final_inventory()

        # Final summary
        success = print_summary(verification_results)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()