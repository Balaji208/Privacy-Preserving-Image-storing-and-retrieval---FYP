"""Model loading utilities"""

import torch
import pickle
from pathlib import Path
from typing import Tuple, Optional
import logging

from .model import DeepHashingHead, DeepHashingModel
from .config import DeepHashingConfig
from ..exceptions import ModelLoadError, PCATransformError

logger = logging.getLogger(__name__)


class ModelLoader:
    """Load deep hashing models and PCA transforms."""
    
    @staticmethod
    def load_deep_hash_model(config: DeepHashingConfig) -> DeepHashingModel:
        """
        Load complete deep hashing pipeline.
        
        Args:
            config: DeepHashingConfig object
        
        Returns:
            DeepHashingModel instance
        
        Raises:
            FileNotFoundError: If model or PCA files not found
            ModelLoadError: If loading fails
        """
        try:
            # Validate hash model path
            hash_path = Path(config.hash_model_path)
            if not hash_path.exists():
                raise FileNotFoundError(f"Hash model not found: {hash_path}")
            
            # Load PCA if in PCA mode
            pca = None
            if config.use_pca:
                if config.pca_transform_path is None:
                    raise ValueError("PCA mode requires pca_transform_path")
                
                pca_path = Path(config.pca_transform_path)
                if not pca_path.exists():
                    raise FileNotFoundError(f"PCA transform not found: {pca_path}")
                
                pca = ModelLoader._load_pca(pca_path)
            
            # Initialize hash model architecture
            hash_model = DeepHashingHead(
                input_dim=config.model_input_dim,
                hidden_dims=config.hidden_dims,
                hash_bits=config.hash_bits,
                dropout=config.dropout
            )
            
            # Wrap in DeepHashingModel
            model = DeepHashingModel(
                pca_transform=pca,
                hash_model=hash_model,
                device=config.device,
                use_pca=config.use_pca
            )
            
            # Load weights
            model.load_weights(str(hash_path))
            
            logger.info(f"✓ Deep hash model loaded successfully")
            
            return model
        
        except Exception as e:
            raise ModelLoadError(f"Failed to load deep hash model: {e}") from e
    
    @staticmethod
    def _load_pca(pca_path: Path):
        """
        Load PCA transform from pickle file.
        
        Args:
            pca_path: Path to PCA pickle file
        
        Returns:
            Fitted PCA object
        
        Raises:
            PCATransformError: If loading fails
        """
        try:
            with open(pca_path, 'rb') as f:
                pca = pickle.load(f)
            
            # Validate PCA object
            if not hasattr(pca, 'transform'):
                raise ValueError("Loaded object is not a valid PCA transformer")
            
            if not hasattr(pca, 'n_components_'):
                raise ValueError("PCA object has not been fitted")
            
            logger.info(f"✓ PCA transform loaded: {pca.n_components_} components")
            logger.info(f"  Explained variance: {pca.explained_variance_ratio_.sum():.2%}")
            
            return pca
        
        except Exception as e:
            raise PCATransformError(f"Failed to load PCA transform: {e}") from e
    
    @staticmethod
    def verify_model(model: DeepHashingModel) -> bool:
        """
        Verify model works correctly with test input.
        
        Args:
            model: DeepHashingModel to verify
        
        Returns:
            True if verification passes, False otherwise
        """
        try:
            # Determine feature dimension based on mode
            feature_dim = 512  # Always use 512D input (before PCA if applicable)
            
            # Test with dummy input
            dummy_features = torch.randn(1, feature_dim)
            
            # Generate hash
            binary, continuous = model.generate_hash(dummy_features)
            
            # Get hash bits from model
            hash_bits = model.hash_model.hash_bits
            
            # Check outputs
            assert binary.shape == (1, hash_bits), \
                f"Wrong binary shape: expected (1, {hash_bits}), got {binary.shape}"
            
            assert continuous.shape == (1, hash_bits), \
                f"Wrong continuous shape: expected (1, {hash_bits}), got {continuous.shape}"
            
            assert binary.min() >= 0 and binary.max() <= 1, \
                f"Binary not in {{0,1}}: range [{binary.min()}, {binary.max()}]"
            
            # Continuous values should be reasonable (not checking strict [-1,1] due to potential scaling)
            assert continuous.min() >= -10 and continuous.max() <= 10, \
                f"Continuous values out of reasonable range: [{continuous.min()}, {continuous.max()}]"
            
            logger.info("✓ Model verification passed")
            logger.info(f"  Input: {feature_dim}D features")
            logger.info(f"  Output: {hash_bits}-bit hash codes")
            logger.info(f"  Binary range: [{binary.min().item()}, {binary.max().item()}]")
            logger.info(f"  Continuous range: [{continuous.min().item():.3f}, {continuous.max().item():.3f}]")
            
            return True
        
        except AssertionError as e:
            logger.error(f"✗ Model verification failed: {e}")
            return False
        
        except Exception as e:
            logger.error(f"✗ Model verification failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def load_and_verify(config: DeepHashingConfig) -> Tuple[DeepHashingModel, bool]:
        """
        Load model and verify it works.
        
        Args:
            config: DeepHashingConfig object
        
        Returns:
            Tuple of (model, verification_passed)
        """
        model = ModelLoader.load_deep_hash_model(config)
        verified = ModelLoader.verify_model(model)
        
        return model, verified
