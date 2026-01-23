"""
Storage Helper Script
=====================
Batch processes and stores all images from sample_images/ folder
using the storage pipeline with DeepHash v4.0.

Usage:
    python storage_helper.py

Features:
- Processes all images in sample_images/
- Stores encrypted images in Azure Blob Storage
- Indexes with 256-bit deep learned hashes (v4.0 direct mode) in Redis
- Encrypts perceptual hashes with FHE
- Generates detailed processing report

Updates in v4.0:
- Uses DeepHash v4.0 (direct 512D → 256-bit, no PCA)
- Updated model paths and architecture
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
import time
import json
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StorageHelper:
    """Helper to batch store images using storage pipeline v4.0."""
    
    def __init__(
        self,
        sample_images_dir: str = "sample_images",
        tenant_id: str = "user_001",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        device: str = "cuda"
    ):
        self.sample_images_dir = Path(sample_images_dir)
        self.tenant_id = tenant_id
        self.device = device
        self.pipeline = None
        self.results = []
        
        # Supported image formats
        self.image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        
        print("=" * 80)
        print("STORAGE HELPER - BATCH IMAGE PROCESSOR (v4.0)")
        print("=" * 80)
        
        # Initialize pipeline
        self._initialize_pipeline(redis_host, redis_port)
    
    def _initialize_pipeline(self, redis_host: str, redis_port: int):
        """Initialize the storage pipeline with v4.0 models."""
        print("\n[STEP 1/3] Initializing Storage Pipeline (v4.0)...")
        
        try:
            from storage_pipeline import SecureImagePipeline, AzureStorageConfig
            
            # Get Azure connection string
            azure_conn = (
                os.getenv("AZURE_STORAGE_CONNECTION_STRING") or
                os.getenv("AZURE_BLOB_STORAGE_CONNECTION_STRING") or
                os.getenv("AZURE_TABLE_STORAGE_CONNECTION_STRING")
            )
            
            if not azure_conn:
                raise ValueError(
                    "Azure connection string not found in .env file\n"
                    "Please set one of:\n"
                    "  - AZURE_STORAGE_CONNECTION_STRING\n"
                    "  - AZURE_BLOB_STORAGE_CONNECTION_STRING\n"
                    "  - AZURE_TABLE_STORAGE_CONNECTION_STRING"
                )
            
            # Create Azure config
            azure_config = AzureStorageConfig(
                connection_string=azure_conn,
                container_name=os.getenv("AZURE_CONTAINER_NAME", "encrypted-images")
            )
            
            # ✅ UPDATED: v4.0 uses direct mode (no PCA)
            self.pipeline = SecureImagePipeline(
                azure_config=azure_config,
                convnext_model_path="models/convnextv2_best_phase1.pt",  # Updated
                deephash_model_path="models/deephash_v4_state_dict.pt",  # v4.0 model
                # No pca_transform_path needed for v4.0!
                redis_host=redis_host,
                redis_port=redis_port,
                tenant_id=self.tenant_id,
                disable_redis=False,
                use_table_metadata=False,  # Optional: set to True for Table Storage
                device=self.device
            )
            
            print("✅ Storage pipeline initialized (v4.0)")
            print(f"   Tenant ID: {self.tenant_id}")
            print(f"   Azure Container: {azure_config.container_name}")
            print(f"   Redis: {redis_host}:{redis_port}")
            print(f"   Device: {self.device}")
            print(f"   Feature Extractor: ConvNeXt-V2 (512D)")
            print(f"   Deep Hash Model: v4.0 Direct Mode (512D → 256-bit, no PCA)")
            print(f"   Architecture: 512D → [1024, 512] → 256-bit")
            
        except FileNotFoundError as e:
            print(f"\n❌ Model files not found: {e}")
            print("\n📁 Required model files:")
            print("   - models/convnext_v2_best_phase1.pt (ConvNeXt V2 feature extractor)")
            print("   - models/deephash_v4_statedict.pt (DeepHash v4.0 weights)")
            print("\n💡 v4.0 no longer requires PCA transform!")
            print("\n📝 Ensure you've trained and exported both files from:")
            print("   - ConvNeXt training notebook")
            print("   - DeepHash v4.0 training notebook")
            sys.exit(1)
        
        except Exception as e:
            print(f"\n❌ Pipeline initialization failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _find_images(self) -> List[Path]:
        """Find all images in sample_images directory."""
        print("\n[STEP 2/3] Scanning for images...")
        
        if not self.sample_images_dir.exists():
            print(f"❌ Directory not found: {self.sample_images_dir}")
            print(f"\n💡 Please create directory and add images:")
            print(f"   mkdir {self.sample_images_dir}")
            return []
        
        images = []
        for ext in self.image_extensions:
            # Case-insensitive search
            images.extend(self.sample_images_dir.glob(f"*{ext}"))
            images.extend(self.sample_images_dir.glob(f"*{ext.upper()}"))
        
        # Remove duplicates and sort
        images = sorted(set(images))
        
        if not images:
            print(f"❌ No images found in {self.sample_images_dir}")
            print(f"\n💡 Supported formats: {', '.join(self.image_extensions)}")
            return []
        
        print(f"✅ Found {len(images)} images:")
        for i, img in enumerate(images, 1):
            size_kb = img.stat().st_size / 1024
            print(f"   {i:2d}. {img.name:<30} ({size_kb:>8.2f} KB)")
        
        return images
    
    def _process_single_image(
        self,
        image_path: Path,
        image_number: int,
        total_images: int
    ) -> Dict:
        """Process a single image."""
        # Generate unique image ID
        timestamp = int(time.time() * 1000)  # milliseconds
        image_id = f"{image_path.stem}_{timestamp}"
        
        print(f"\n[{image_number}/{total_images}] Processing: {image_path.name}")
        print(f"   Image ID: {image_id}")
        
        start_time = time.time()
        
        try:
            # Process through pipeline
            returned_id, metadata = self.pipeline.process_image(
                str(image_path),
                image_id
            )
            
            elapsed = time.time() - start_time
            
            # Build result
            result = {
                'success': True,
                'image_path': str(image_path),
                'image_name': image_path.name,
                'image_id': image_id,
                'blob_name': metadata.azure_row_key,
                'fhe_ciphertext_size': metadata.fhe_ciphertext_size,
                'deephash_sum': metadata.deephash_sum,
                'processing_time': elapsed,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"   ✅ Success in {elapsed:.2f}s")
            print(f"   FHE CT Size: {metadata.fhe_ciphertext_size:,} bytes")
            print(f"   DeepHash: {metadata.deephash_sum}/256 bits set")
            print(f"   Blob: {metadata.azure_row_key[:50]}...")
            
            return result
        
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Failed: {e}")
            logger.error(f"Failed to process {image_path.name}: {e}", exc_info=True)
            
            return {
                'success': False,
                'image_path': str(image_path),
                'image_name': image_path.name,
                'image_id': image_id,
                'error': str(e),
                'processing_time': elapsed,
                'timestamp': datetime.now().isoformat()
            }
    
    def process_all_images(self):
        """Process all images in sample_images directory."""
        # Find images
        images = self._find_images()
        if not images:
            print("\n❌ No images to process")
            return
        
        print("\n[STEP 3/3] Processing images...")
        print("=" * 80)
        
        total_start_time = time.time()
        
        # Process each image
        for i, image_path in enumerate(images, 1):
            result = self._process_single_image(image_path, i, len(images))
            self.results.append(result)
            
            # Brief pause between images (optional, helps with rate limiting)
            if i < len(images):
                time.sleep(0.5)
        
        total_elapsed = time.time() - total_start_time
        
        # Generate summary
        self._print_summary(total_elapsed)
        
        # Save report
        self._save_report()
    
    def _print_summary(self, total_time: float):
        """Print processing summary."""
        print("\n" + "=" * 80)
        print("PROCESSING SUMMARY")
        print("=" * 80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r['success'])
        failed = total - successful
        
        print(f"\n{'Total images:':<25} {total}")
        print(f"{'✅ Successfully processed:':<25} {successful}")
        print(f"{'❌ Failed:':<25} {failed}")
        print(f"{'Total time:':<25} {total_time:.2f}s")
        
        if successful > 0:
            avg_time = sum(r['processing_time'] for r in self.results if r['success']) / successful
            print(f"{'Average time per image:':<25} {avg_time:.2f}s")
            
            # Calculate total storage
            total_fhe_size = sum(
                r.get('fhe_ciphertext_size', 0)
                for r in self.results
                if r['success']
            )
            print(f"{'Total FHE CT size:':<25} {total_fhe_size / (1024*1024):.2f} MB")
        
        print("\n" + "=" * 80)
        
        if failed > 0:
            print("\n⚠️ FAILED IMAGES:")
            for r in self.results:
                if not r['success']:
                    print(f"   - {r['image_name']}: {r.get('error', 'Unknown error')}")
        
        if successful == total:
            print("\n🎉 ALL IMAGES PROCESSED SUCCESSFULLY!")
            print("✅ Images are now:")
            print("   - Encrypted and stored in Azure Blob Storage")
            print("   - Indexed with 256-bit deep hashes (v4.0) in Redis")
            print("   - Searchable via similarity search")
            print("   - Using direct mode (no PCA preprocessing)")
        else:
            print(f"\n⚠️ {failed}/{total} images failed to process")
    
    def _save_report(self):
        """Save processing report to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(f"storage_report_{timestamp}.json")
        
        report = {
            'pipeline_version': '4.0',
            'tenant_id': self.tenant_id,
            'timestamp': datetime.now().isoformat(),
            'device': self.device,
            'total_images': len(self.results),
            'successful': sum(1 for r in self.results if r['success']),
            'failed': sum(1 for r in self.results if not r['success']),
            'model_info': {
                'feature_extractor': 'ConvNeXt-V2 (512D)',
                'deep_hash': 'v4.0 Direct Mode (512D → 256-bit, no PCA)',
                'architecture': '512D → [1024, 512] → 256-bit',
                'similarity_threshold': '66 bits',
                'expected_similar_distance': '40-66 bits (high confidence)',
                'expected_dissimilar_distance': '120+ bits (very low confidence)',
                'improvements': [
                    'Removed PCA preprocessing (faster inference)',
                    'Direct 512D → 256-bit mapping',
                    'Research-backed architecture from v4.0 training',
                    'Adaptive margin triplet loss',
                    'Cauchy quantization for better gradients'
                ]
            },
            'results': self.results
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Report saved: {report_file}")
        
        except Exception as e:
            print(f"\n⚠️ Failed to save report: {e}")


def main():
    """Main entry point."""
    # Check if sample_images directory exists
    sample_dir = Path("sample_images")
    
    if not sample_dir.exists():
        print("=" * 80)
        print("SAMPLE IMAGES DIRECTORY NOT FOUND")
        print("=" * 80)
        print(f"\n💡 Please create directory and add images:")
        print(f"   mkdir sample_images")
        print(f"   copy your_images/* sample_images/")
        print(f"\n📁 Supported formats: .jpg, .jpeg, .png, .bmp, .gif")
        return
    
    # Auto-detect device
    try:
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"\n🖥️  Using device: {device.upper()}")
    except ImportError:
        device = 'cpu'
        print(f"\n🖥️  Using device: CPU (PyTorch not detected)")
    
    # Initialize helper
    helper = StorageHelper(
        sample_images_dir="sample_images",
        tenant_id="user_001",
        redis_host="localhost",
        redis_port=6379,
        device=device
    )
    
    # Process all images
    helper.process_all_images()
    
    print("\n" + "=" * 80)
    print("STORAGE HELPER COMPLETE (v4.0)")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
