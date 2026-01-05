"""Check which imports work."""

import sys
from pathlib import Path

print("Python path:")
for p in sys.path:
    print(f"  {p}")

print("\n" + "="*70)
print("Checking imports...")
print("="*70)

# Check 1: deephashing
print("\n[1] Checking deephashing...")
try:
    import deephashing
    print(f"✓ deephashing imported")
    print(f"  Location: {deephashing.__file__}")
    print(f"  Contents: {dir(deephashing)}")
except ImportError as e:
    print(f"✗ Failed: {e}")

# Check 2: deephashing.generator
print("\n[2] Checking deephashing.generator...")
try:
    from deephashing.generator import DeepHashGenerator
    print(f"✓ DeepHashGenerator imported")
except ImportError as e:
    print(f"✗ Failed: {e}")

# Check 3: feature_extractor
print("\n[3] Checking feature_extractor...")
try:
    import feature_extractor
    print(f"✓ feature_extractor imported")
    print(f"  Location: {feature_extractor.__file__}")
    print(f"  Contents: {dir(feature_extractor)}")
except ImportError as e:
    print(f"✗ Failed: {e}")

# Check 4: feature_extractor.convnext_extractor
print("\n[4] Checking feature_extractor.convnext_extractor...")
try:
    from feature_extractor.convnext_extractor import ConvNeXtFeatureExtractor
    print(f"✓ ConvNeXtFeatureExtractor imported")
except ImportError as e:
    print(f"✗ Failed: {e}")

# Check 5: List actual files
print("\n" + "="*70)
print("Actual directory structure:")
print("="*70)

print("\ndeephashing/:")
dh_dir = Path("./deephashing")
if dh_dir.exists():
    for f in sorted(dh_dir.glob("*.py")):
        print(f"  {f.name}")
else:
    print("  (not found)")

print("\nfeature_extractor/:")
fe_dir = Path("./feature_extractor")
if fe_dir.exists():
    for f in sorted(fe_dir.glob("*.py")):
        print(f"  {f.name}")
else:
    print("  (not found)")

print("\n" + "="*70)
