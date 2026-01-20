"""
BFV Key Extractor from .env
============================

Extracts BFV public context from TENSEAL_BFV_CONTEXT in .env file.

Usage:
    python extract_bfv_keys_from_env.py
"""

import os
import sys
import json
import base64
import tenseal as ts
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class BFVKeyExtractor:
    """Extract BFV keys from .env file."""

    def __init__(self):
        self.context = None

    def load_context_from_env(self) -> ts.Context:
        """Load TenSEAL context from .env file."""
        print("=" * 80)
        print("BFV KEY EXTRACTOR - From .env File".center(80))
        print("=" * 80)
        print()

        print("[1/4] Loading TenSEAL context from .env...")

        # Get context from .env
        context_b64 = os.getenv('TENSEAL_BFV_CONTEXT')

        if not context_b64:
            raise RuntimeError(
                "TENSEAL_BFV_CONTEXT not found in .env file!\n"
                "Make sure your .env contains:\n"
                "TENSEAL_BFV_CONTEXT=<base64_encoded_context>"
            )

        print(f"      ✅ Found in .env (base64: {len(context_b64)} chars)")

        # Decode base64
        try:
            context_bytes = base64.b64decode(context_b64)
            print(f"      ✅ Decoded: {len(context_bytes):,} bytes")
        except Exception as e:
            raise RuntimeError(f"Failed to decode base64: {e}")

        # Deserialize context
        try:
            self.context = ts.context_from(context_bytes)
            print(f"      ✅ Context deserialized")
            print(f"         Scheme: BFV")
            print(f"         Poly modulus degree: {self.context.poly_modulus_degree}")
            print(f"         Plain modulus: {self.context.plain_modulus}")
            print(f"         Has secret key: {self.context.is_private()}")
            print()
            return self.context
        except Exception as e:
            raise RuntimeError(f"Failed to deserialize context: {e}")

    def extract_public_context(self, output_dir: str = "bfv_keys"):
        """Extract full public context."""
        print("[2/4] Extracting public context (includes all keys)...")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Create a copy
        context_copy = ts.context_from(self.context.serialize())

        # Make it public (removes secret key)
        print("      Removing secret key...")
        context_copy.make_context_public()
        print(f"      ✅ Secret key removed")
        print(f"         Is public: {context_copy.is_public()}")

        # Serialize public context
        public_context_bytes = context_copy.serialize()

        # Save binary file
        context_file = output_path / "bfv_context_public.bin"
        with open(context_file, 'wb') as f:
            f.write(public_context_bytes)

        print(f"      ✅ Saved: {context_file}")
        print(f"         Size: {len(public_context_bytes):,} bytes")
        print(f"         Contains: Public key + Relin keys + Galois keys")
        print()

        return {
            'file': str(context_file),
            'size': len(public_context_bytes),
            'is_public': context_copy.is_public()
        }

    def extract_parameters(self, output_dir: str = "bfv_keys"):
        """Extract and save BFV parameters."""
        print("[3/4] Extracting BFV parameters...")

        output_path = Path(output_dir)

        params = {
            'scheme': 'BFV',
            'poly_modulus_degree': self.context.poly_modulus_degree,
            'plain_modulus': self.context.plain_modulus,
        }

        params_file = output_path / "bfv_params.json"
        with open(params_file, 'w') as f:
            json.dump(params, f, indent=2)

        print(f"      ✅ Saved: {params_file}")
        print(f"         Poly modulus degree: {params['poly_modulus_degree']}")
        print(f"         Plain modulus: {params['plain_modulus']}")
        print()

        return params

    def verify_extraction(self, context_file: str):
        """Verify extracted context."""
        print("[4/4] Verifying extracted context...")

        with open(context_file, 'rb') as f:
            ctx = ts.context_from(f.read())

        print(f"      ✅ Context loaded from file")
        print(f"         Is public: {ctx.is_public()}")
        print(f"         Poly modulus: {ctx.poly_modulus_degree}")
        print()

        # Test encryption
        test_vector = [1, 2, 3, 4, 5]
        encrypted = ts.bfv_vector(ctx, test_vector)
        print(f"      ✅ Encryption test passed")
        print(f"         Input: {test_vector}")
        print(f"         Encrypted size: {len(encrypted.serialize()):,} bytes")
        print()

        # Test homomorphic operations
        v1 = ts.bfv_vector(ctx, [10, 20, 30])
        v2 = ts.bfv_vector(ctx, [5, 10, 15])
        sum_ct = v1 + v2
        print(f"      ✅ Homomorphic operations work")
        print()

        # Test decryption (should fail)
        try:
            encrypted.decrypt()
            print(f"      ❌ ERROR: Should not decrypt!")
        except:
            print(f"      ✅ Decryption blocked (no secret key)")
        print()

def main():
    try:
        extractor = BFVKeyExtractor()
        extractor.load_context_from_env()
        result = extractor.extract_public_context()
        extractor.extract_parameters()
        extractor.verify_extraction(result['file'])

        print("=" * 80)
        print("✅ EXTRACTION COMPLETE".center(80))
        print("=" * 80)
        print()
        print(f"📁 Output: bfv_keys/")
        print(f"📄 Main file: bfv_context_public.bin ({result['size']:,} bytes)")
        print()
        print("🚀 NEXT STEPS:")
        print("   1. Copy bfv_context_public.bin to similarity server:")
        print("      scp bfv_keys/bfv_context_public.bin user@server:/path/")
        print()
        print("   2. Load in Python:")
        print("      import tenseal as ts")
        print("      context = ts.context_from(open('bfv_context_public.bin', 'rb').read())")
        print()
        print("   3. Use for homomorphic operations:")
        print("      encrypted = ts.bfv_vector(context, [1, 0, 1, 1, 0])")
        print()
        print("🔒 SECURITY:")
        print("   ✅ Public context safe for untrusted servers")
        print("   ✅ Contains: Public key, Relin keys, Galois keys")
        print("   ❌ Cannot: Decrypt (no secret key)")
        print("   🔑 Secret key stays in your .env file!")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()