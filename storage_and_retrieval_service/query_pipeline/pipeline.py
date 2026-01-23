"""
Query Pipeline
==============
Complete pipeline for preparing similarity search queries (v4.0)
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, List

from .image_processor import ImageProcessor
from .token_generator import TokenGenerator
from .fhe_encryptor import FHEEncryptor

logger = logging.getLogger(__name__)


class QueryPipeline:
    """Complete query preparation pipeline (v4.0 - no PCA)."""
    
    def __init__(
        self,
        convnext_model_path: str = './models/convnextv2_best_phase1.pt',
        deephash_model_path: str = './models/deephash_v4_state_dict.pt',
        bfv_context_path: str = './bfv_keys/bfv_context_public.bin',
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        device: str = 'cuda'
    ):
        """
        Initialize query pipeline (v4.0).
        
        Args:
            convnext_model_path: Path to ConvNeXt-V2 model
            deephash_model_path: Path to DeepHash v4.0 model
            bfv_context_path: Path to BFV context
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            device: Device for ML models
        
        Note:
            v4.0 no longer requires pca_transform_path parameter!
        """
        logger.info("=" * 80)
        logger.info("QUERY PIPELINE INITIALIZATION (v4.0)")
        logger.info("=" * 80)
        
        # Initialize components
        logger.info("\n[1/3] Loading image processor...")
        self.image_processor = ImageProcessor(
            convnext_model_path=convnext_model_path,
            deephash_model_path=deephash_model_path,
            device=device
        )
        logger.info("✓ Image processor loaded (v4.0)")
        logger.info("  - ConvNeXt-V2: 512D features")
        logger.info("  - DeepHash v4.0: Direct mode (512D → 256-bit, no PCA)")
        logger.info("  - Architecture: 512D → [1024, 512] → 256-bit")
        
        logger.info("\n[2/3] Loading token generator...")
        self.token_generator = TokenGenerator(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db
        )
        logger.info("✓ Token generator loaded")
        
        logger.info("\n[3/3] Loading FHE encryptor...")
        self.fhe_encryptor = FHEEncryptor(
            context_path=bfv_context_path
        )
        logger.info("✓ FHE encryptor loaded")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ QUERY PIPELINE READY (v4.0)")
        logger.info("=" * 80)
        logger.info("")
    
    def prepare_query(
        self,
        image_path: str,
        tenant_id: str = "user_001",
        top_k: int = 5
    ) -> Dict:
        """
        Prepare complete query request.
        
        Args:
            image_path: Path to query image
            tenant_id: Tenant identifier
            top_k: Number of results to retrieve
        
        Returns:
            Dict ready for POST to /api/v1/search:
            {
                "query_fhe_ct": "base64_encoded_ciphertext",
                "tokens": ["token1", "token2", ...],
                "tenant_id": "user_001",
                "top_k": 5
            }
        """
        image_path = Path(image_path)
        
        logger.info("=" * 80)
        logger.info(f"PREPARING QUERY: {image_path.name}")
        logger.info("=" * 80)
        
        # Step 1: Process image (ConvNeXt → DeepHash v4.0 direct)
        logger.info("\n[STEP 1/3] Processing image (v4.0)...")
        logger.info(f"  Input: {image_path.name}")
        
        features, binary_hash = self.image_processor.process(str(image_path))
        
        ones_count = int(np.sum(binary_hash))
        logger.info(f"[STEP 1/3] ✓ Extracted:")
        logger.info(f"  Features: {features.shape} (512D)")
        logger.info(f"  Hash: {binary_hash.shape} (256-bit, v4.0 direct mode)")
        logger.info(f"  Hash density: {ones_count}/256 ({ones_count/256*100:.1f}%)")
        
        # Step 2: Generate LSH tokens (6 tables × 12 bits each)
        logger.info("\n[STEP 2/3] Generating LSH tokens...")
        tokens = self.token_generator.generate(binary_hash, tenant_id)
        
        logger.info(f"[STEP 2/3] ✓ Generated {len(tokens)} tokens")
        logger.info(f"  LSH config: 6 tables × 12 bits")
        
        # Step 3: Encrypt hash with FHE (BFV scheme)
        logger.info("\n[STEP 3/3] Encrypting hash with FHE...")
        fhe_ciphertext = self.fhe_encryptor.encrypt(binary_hash)
        
        logger.info(f"[STEP 3/3] ✓ Encrypted:")
        logger.info(f"  Ciphertext size: {len(fhe_ciphertext):,} chars")
        logger.info(f"  Encoding: Base64")
        
        # Build request
        request = {
            "query_fhe_ct": fhe_ciphertext,
            "tokens": tokens,
            "tenant_id": tenant_id,
            "top_k": top_k
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ QUERY PREPARATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Request summary:")
        logger.info(f"  Request size: {len(str(request)):,} chars")
        logger.info(f"  Tokens: {len(tokens)}")
        logger.info(f"  Top-K: {top_k}")
        logger.info(f"  Ready for: POST /api/v1/search")
        logger.info("=" * 80)
        
        return request
    
    def get_info(self) -> dict:
        """Get pipeline information."""
        return {
            'version': '4.0',
            'image_processor': self.image_processor.get_info(),
            'token_generator': {
                'num_tables': 6,
                'bits_per_table': 12,
                'hash_length': 256
            },
            'fhe_encryptor': {
                'scheme': 'BFV',
                'context_path': self.fhe_encryptor.context_path
            },
            'pipeline_flow': [
                '1. Image → ConvNeXt-V2 → 512D features',
                '2. Features → DeepHash v4.0 (direct) → 256-bit binary code',
                '3. Hash → LSH → 6 bucket tokens',
                '4. Hash → FHE → Encrypted ciphertext',
                '5. Build query request'
            ]
        }
