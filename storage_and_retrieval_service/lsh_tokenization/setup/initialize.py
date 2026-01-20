"""
LSH Initialization Module
==========================
Command-line tool to initialize LSH with HMAC keys.

Usage:
    python -m lsh_tokenization.setup.initialize
"""

import sys
from pathlib import Path

# Ensure proper imports
try:
    from .lsh_key_setup import LSHKeySetup
except ImportError:
    # If run as script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from lsh_tokenization.setup.lsh_key_setup import LSHKeySetup


def main():
    """Initialize LSH HMAC key in SoftHSM."""
    print("\n" + "=" * 70)
    print("LSH HMAC Key Initialization")
    print("=" * 70)
    
    try:
        # Check current status
        print("\n[Step 1/2] Checking current setup...")
        LSHKeySetup.print_setup_status()
        
        # Initialize key
        print("\n[Step 2/2] Initializing HMAC key in SoftHSM...")
        hmac_key = LSHKeySetup.initialize_hmac_key(overwrite=False)
        
        print(f"\n✓ HMAC key initialized successfully!")
        print(f"  Key (first 16 chars): {hmac_key.hex()[:16]}...")
        print(f"  Key length: {len(hmac_key)} bytes")
        
        # Verify
        print("\n[Verification] Checking setup again...")
        LSHKeySetup.print_setup_status()
        
        print("\n" + "=" * 70)
        print("✅ Initialization Complete!")
        print("=" * 70)
        print("\nYou can now run:")
        print("  python test_lsh_with_deephash.py")
        print("  pytest tests/test_lsh.py")
        print("\n" + "=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
