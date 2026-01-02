"""
Medical Image Hashing - Complete Pipeline
==========================================
End-to-end demonstration of:
1. Feature extraction using ConvNeXt-V2
2. Binary hash generation using DeepHash
3. Similarity computation and retrieval

Author: Medical Image Hashing Project
Date: 2026-01-02
Version: 2.0.0
"""

import numpy as np
from pathlib import Path
import sys
from typing import List, Tuple

# ✅ ADD PARENT DIRECTORY TO PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now import normally
from feature_extractor import ConvNeXtFeatureExtractor
from deephashing import DeepHashGenerator


def print_header(title: str, width: int = 70) -> None:
    """Print formatted header"""
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)


def print_step(step: int, description: str) -> None:
    """Print step information"""
    print(f"\n[Step {step}] {description}")


def validate_files(paths: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate file existence.
    
    Args:
        paths: List of file paths to check
        
    Returns:
        Tuple of (existing_paths, missing_paths)
    """
    existing = []
    missing = []
    
    for path in paths:
        if Path(path).exists():
            existing.append(path)
        else:
            missing.append(path)
    
    return existing, missing


def display_similarity_matrix(similarities: np.ndarray, names: List[str] = None) -> None:
    """
    Display formatted similarity matrix.
    
    Args:
        similarities: Similarity matrix
        names: Optional list of image names
    """
    n = similarities.shape[0]
    
    # Create names if not provided
    if names is None:
        names = [f"Img{i}" for i in range(n)]
    
    # Header
    col_width = 7
    header = "      " + "".join([f"{name[:5]:>{col_width}}" for name in names])
    print(f"\n  {header}")
    print("  " + "-" * (6 + col_width * n))
    
    # Rows
    for i in range(n):
        row_name = f"{names[i][:5]:>5}"
        row_values = "".join([f"{similarities[i, j]:>{col_width}.3f}" for j in range(n)])
        print(f"  {row_name} {row_values}")


def find_extremes(
    similarities: np.ndarray,
    images: List[str]
) -> Tuple[Tuple[int, int, float], Tuple[int, int, float]]:
    """
    Find most and least similar image pairs.
    
    Args:
        similarities: Similarity matrix
        images: List of image paths
        
    Returns:
        Tuple of ((max_i, max_j, max_sim), (min_i, min_j, min_sim))
    """
    # Copy and exclude diagonal
    sim_copy = similarities.copy()
    np.fill_diagonal(sim_copy, -1)
    
    # Most similar
    max_idx = np.unravel_index(sim_copy.argmax(), sim_copy.shape)
    max_sim = sim_copy[max_idx]
    
    # Least similar (exclude diagonal by setting to inf)
    sim_copy_min = similarities.copy()
    np.fill_diagonal(sim_copy_min, np.inf)
    min_idx = np.unravel_index(sim_copy_min.argmin(), sim_copy_min.shape)
    min_sim = sim_copy_min[min_idx]
    
    return (max_idx[0], max_idx[1], max_sim), (min_idx[0], min_idx[1], min_sim)


def main():
    """Main pipeline execution"""
    
    print_header("Medical Image Hashing - Complete Pipeline")
    
    # ========================================================================
    # Configuration
    # ========================================================================
    
    # ✅ UPDATE PATHS: Go up one level from tests/ folder
    BASE_DIR = Path(__file__).parent.parent
    
    # Model paths
    FEATURE_MODEL = BASE_DIR / 'models/convnext_state_dict_only.pt'
    HASH_MODEL = BASE_DIR / 'models/deephash_state_dict_only.pt'
    
    # Sample images
    IMAGE_PATHS = [
        str(BASE_DIR / 'sample_images/003412_03_01_108.png'),
        str(BASE_DIR / 'sample_images/1 (68).jpg'),
        str(BASE_DIR / 'sample_images/sample.jpg')
    ]
    
    # ========================================================================
    # STEP 1: Initialize Models
    # ========================================================================
    print_step(1, "Initializing models...")
    
    # Validate model files
    if not FEATURE_MODEL.exists():
        raise FileNotFoundError(f"Feature model not found: {FEATURE_MODEL}")
    if not HASH_MODEL.exists():
        raise FileNotFoundError(f"Hash model not found: {HASH_MODEL}")
    
    # Initialize
    feature_extractor = ConvNeXtFeatureExtractor(str(FEATURE_MODEL))
    hash_generator = DeepHashGenerator(str(HASH_MODEL))
    
    print("  ✓ Feature extractor initialized")
    print("  ✓ Hash generator initialized")
    
    # ========================================================================
    # STEP 2: Single Image Processing
    # ========================================================================
    print_step(2, "Processing single image...")
    
    single_image = IMAGE_PATHS[0]
    
    if not Path(single_image).exists():
        print(f"  ⚠ Warning: Image not found: {single_image}")
        print("  Skipping single image test...")
    else:
        # Extract features
        features = feature_extractor.extract(single_image)
        
        print(f"  Image: {Path(single_image).name}")
        print(f"  Features shape: {features.shape}")
        print(f"  Features L2 norm: {np.linalg.norm(features):.4f}")
        
        # Generate hash
        hash_code = hash_generator.generate(features)
        
        print(f"\n  Hash code:")
        print(f"    Shape: {hash_code.shape}")
        print(f"    Bits: {len(hash_code)}")
        print(f"    Ones: {hash_code.sum()}/{len(hash_code)} ({hash_code.sum()/len(hash_code)*100:.1f}%)")
        print(f"    Zeros: {len(hash_code) - hash_code.sum()}/{len(hash_code)}")
    
    # ========================================================================
    # STEP 3: Batch Processing
    # ========================================================================
    print_step(3, "Processing batch of images...")
    
    # Validate images
    existing_images, missing_images = validate_files(IMAGE_PATHS)
    
    if len(existing_images) == 0:
        print("  ❌ No images found!")
        print("  Please add sample images to ./sample_images/")
        return
    
    if missing_images:
        print(f"  ⚠ Warning: {len(missing_images)} image(s) not found:")
        for img in missing_images:
            print(f"    - {img}")
    
    print(f"  Processing {len(existing_images)} image(s)...")
    
    # Extract features
    batch_features = feature_extractor.extract_batch(existing_images)
    print(f"  ✓ Extracted features: {batch_features.shape}")
    
    # Generate hashes
    batch_hashes = hash_generator.generate_batch(batch_features)
    print(f"  ✓ Generated hashes: {batch_hashes.shape}")
    
    # ========================================================================
    # STEP 4: Similarity Computation
    # ========================================================================
    print_step(4, "Computing pairwise similarities...")
    
    similarities = hash_generator.compute_similarity(batch_hashes, batch_hashes)
    
    print(f"  Similarity matrix shape: {similarities.shape}")
    print(f"  Self-similarities (diagonal): {np.diag(similarities)}")
    
    # Display matrix
    image_names = [Path(img).stem[:10] for img in existing_images]
    display_similarity_matrix(similarities, image_names)
    
    # ========================================================================
    # STEP 5: Find Similar and Dissimilar Pairs
    # ========================================================================
    print_step(5, "Analyzing image pairs...")
    
    (max_i, max_j, max_sim), (min_i, min_j, min_sim) = find_extremes(
        similarities,
        existing_images
    )
    
    # Most similar pair
    print(f"\n  📊 Most similar pair:")
    print(f"    Image A: {Path(existing_images[max_i]).name}")
    print(f"    Image B: {Path(existing_images[max_j]).name}")
    print(f"    Similarity: {max_sim:.4f} ({max_sim*100:.1f}%)")
    
    hamming_max = hash_generator.compute_hamming_distance(
        batch_hashes[max_i],
        batch_hashes[max_j]
    )
    print(f"    Hamming distance: {hamming_max}/{len(batch_hashes[0])} bits")
    print(f"    Matching bits: {len(batch_hashes[0]) - hamming_max}")
    
    # Least similar pair
    print(f"\n  📊 Least similar pair:")
    print(f"    Image A: {Path(existing_images[min_i]).name}")
    print(f"    Image B: {Path(existing_images[min_j]).name}")
    print(f"    Similarity: {min_sim:.4f} ({min_sim*100:.1f}%)")
    
    hamming_min = hash_generator.compute_hamming_distance(
        batch_hashes[min_i],
        batch_hashes[min_j]
    )
    print(f"    Hamming distance: {hamming_min}/{len(batch_hashes[0])} bits")
    print(f"    Matching bits: {len(batch_hashes[0]) - hamming_min}")
    
    # ========================================================================
    # STEP 6: System Statistics
    # ========================================================================
    print_step(6, "System information...")
    
    # Feature extractor info
    extractor_info = feature_extractor.get_info()
    print(f"\n  🔬 Feature Extractor:")
    print(f"    Model: ConvNeXt-V2 ({extractor_info.get('model_size', 'unknown')})")
    print(f"    Feature dimension: {extractor_info['feature_dim']}")
    print(f"    Device: {extractor_info['device']}")
    
    # Hash generator info
    hash_info = hash_generator.get_info()
    print(f"\n  🔐 Hash Generator:")
    print(f"    Model: DeepHash")
    print(f"    Hash bits: {hash_info['hash_bits']}")
    print(f"    Device: {hash_info['device']}")
    
    if 'metrics' in hash_info and hash_info['metrics']:
        metrics = hash_info['metrics']
        print(f"\n  📈 Performance Metrics:")
        print(f"    mAP: {metrics.get('map', 0):.4f}")
        print(f"    Similar images distance: {metrics.get('hamming_similar_mean', 0):.2f} bits")
        print(f"    Dissimilar images distance: {metrics.get('hamming_dissimilar_mean', 0):.2f} bits")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print_header("✅ Pipeline Complete!", 70)
    
    n = len(existing_images)
    
    print("\n  📋 Summary:")
    print(f"    Processed: {n} image(s)")
    print(f"    Features: {batch_features.shape[0]} × {batch_features.shape[1]}D")
    print(f"    Hashes: {batch_hashes.shape[0]} × {batch_hashes.shape[1]} bits")
    print(f"    Similarity scores: {similarities.size}")
    
    print("\n  📊 Statistics:")
    print(f"    Highest similarity: {max_sim:.4f}")
    print(f"    Lowest similarity: {min_sim:.4f}")
    
    # Average similarity (excluding diagonal)
    if n > 1:
        avg_sim = (similarities.sum() - n) / (n * (n - 1))
        print(f"    Average similarity: {avg_sim:.4f}")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}")
        print("Please ensure all required files exist.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠ Pipeline interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
