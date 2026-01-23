"""Main DeepHash generator API"""

import torch
import numpy as np
import pickle
from pathlib import Path
from typing import Union, Tuple, Optional
import logging

from .core.model import DeepHashingHead, DeepHashingModel
from .core.config import DeepHashingConfig
from .exceptions import HashGenerationError, ModelLoadError, PCATransformError

logger = logging.getLogger(__name__)


class DeepHashGenerator:
    """
    DeepHash binary code generator with optional PCA preprocessing.
    
    Supports two initialization modes:
        1. Config-based (RECOMMENDED): DeepHashGenerator(config=config)
        2. Path-based (Legacy): DeepHashGenerator(model_path='...', pca_path='...')
    
    Example (v4.0 Direct Mode):
        >>> config = DeepHashingConfig(
        ...     hash_model_path='models/deephash_v4_statedict.pt',
        ...     pca_transform_path=None  # No PCA for v4.0
        ... )
        >>> generator = DeepHashGenerator(config=config)
        >>> binary, continuous = generator.generate_hash(features)
    
    Example (Legacy PCA Mode):
        >>> config = DeepHashingConfig(
        ...     hash_model_path='models/deephash_state_dict_only.pt',
        ...     pca_transform_path='models/pca_whitening.pkl'
        ... )
        >>> generator = DeepHashGenerator(config=config)
        >>> binary, continuous = generator.generate_hash(features)
    """
    
    def __init__(
        self,
        config: Optional[DeepHashingConfig] = None,
        model_path: Optional[Union[str, Path]] = None,
        pca_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None
    ):
        """
        Initialize generator.
        
        Args:
            config: DeepHashingConfig object (RECOMMENDED)
            model_path: Path to model weights (Legacy API)
            pca_path: Path to PCA transform (Legacy API, None for direct mode)
            device: Device override
        """
        
        # Handle config-based initialization (RECOMMENDED)
        if config is not None:
            self.config = config
        
        # Handle path-based initialization (Legacy - backward compatibility)
        elif model_path is not None:
            logger.warning(
                "Path-based initialization is deprecated. "
                "Use DeepHashingConfig instead."
            )
            
            self.config = DeepHashingConfig(
                hash_model_path=str(model_path),
                pca_transform_path=str(pca_path) if pca_path else None,
                device=device or 'cuda'
            )
        
        else:
            raise ValueError(
                "Must provide either 'config' or 'model_path'. "
                "Example: DeepHashGenerator(config=DeepHashingConfig(...))"
            )
        
        # Override device if specified
        if device is not None:
            self.config.device = device
        
        # Auto-detect device
        if self.config.device == 'cuda' and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.config.device = 'cpu'
        
        # Load PCA transform if in PCA mode
        if self.config.use_pca:
            self.pca = self._load_pca()
        else:
            self.pca = None
            logger.info("Running in direct mode (no PCA preprocessing)")
        
        # Initialize hash model
        self.hash_model = self._initialize_model()
        
        # Wrap in DeepHashingModel
        self.model = DeepHashingModel(
            pca_transform=self.pca,
            hash_model=self.hash_model,
            device=self.config.device,
            use_pca=self.config.use_pca
        )
        
        # Load weights
        self.model.load_weights(self.config.hash_model_path)
        
        # Log initialization summary
        self._log_initialization()
    
    def _load_pca(self):
        """Load PCA transform"""
        if self.config.pca_transform_path is None:
            return None
        
        pca_path = Path(self.config.pca_transform_path)
        
        if not pca_path.exists():
            raise FileNotFoundError(
                f"PCA transform not found: {pca_path}\n"
                "Please ensure you have exported the PCA model from training."
            )
        
        try:
            with open(pca_path, 'rb') as f:
                pca = pickle.load(f)
            
            logger.info(f"✓ PCA transform loaded from {pca_path.name}")
            logger.info(f"  Components: {pca.n_components_}")
            logger.info(f"  Explained variance: {pca.explained_variance_ratio_.sum():.2%}")
            
            return pca
        
        except Exception as e:
            raise PCATransformError(f"Failed to load PCA: {e}") from e
    
    def _initialize_model(self) -> DeepHashingHead:
        """Initialize hash model architecture"""
        return DeepHashingHead(
            input_dim=self.config.model_input_dim,
            hidden_dims=self.config.hidden_dims,
            hash_bits=self.config.hash_bits,
            dropout=self.config.dropout
        )
    
    def _log_initialization(self):
        """Log initialization summary"""
        logger.info("✓ DeepHash generator initialized")
        logger.info(f"  Mode: {'PCA' if self.config.use_pca else 'Direct'}")
        logger.info(f"  Input: {self.config.feature_dim}D features")
        
        if self.config.use_pca:
            logger.info(f"  PCA: {self.config.feature_dim}D → {self.config.pca_dim}D")
        
        logger.info(f"  Hash: {self.config.hash_bits}-bit codes")
        logger.info(f"  Architecture: {self.config.model_input_dim}D → {self.config.hidden_dims} → {self.config.hash_bits}D")
        logger.info(f"  Device: {self.config.device}")
    
    @torch.no_grad()
    def generate_hash(
        self,
        features: Union[np.ndarray, torch.Tensor]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate hash codes from features (RECOMMENDED API).
        
        Args:
            features: Feature vector(s)
                - Single: [512] or [1, 512]
                - Batch: [N, 512]
        
        Returns:
            Tuple of:
                - binary_hash: Binary codes [N, 256] in {0, 1}
                - continuous_hash: Continuous codes [N, 256]
        
        Raises:
            HashGenerationError: If generation fails
        """
        try:
            # Validate input
            if isinstance(features, np.ndarray):
                features = torch.from_numpy(features).float()
            
            if features.ndim == 1:
                features = features.unsqueeze(0)
            
            # Check dimensions
            if features.shape[-1] != self.config.feature_dim:
                raise ValueError(
                    f"Expected features with dim {self.config.feature_dim}, "
                    f"got {features.shape[-1]}"
                )
            
            # Generate hash
            binary_hash, continuous_hash = self.model.generate_hash(features)
            
            # Convert to numpy
            binary_np = binary_hash.cpu().numpy().astype(np.uint8)
            continuous_np = continuous_hash.cpu().numpy().astype(np.float32)
            
            return binary_np, continuous_np
        
        except Exception as e:
            raise HashGenerationError(
                f"Failed to generate hash: {e}"
            ) from e
    
    @torch.no_grad()
    def generate(
        self,
        features: np.ndarray
    ) -> np.ndarray:
        """
        Generate binary hash (Legacy API - backward compatibility).
        
        Args:
            features: Feature vector [512] or batch [N, 512]
        
        Returns:
            Binary hash codes [256] or [N, 256] in {0, 1}
        """
        binary_hash, _ = self.generate_hash(features)
        return binary_hash.squeeze() if binary_hash.shape[0] == 1 else binary_hash
    
    def compute_similarity(
        self,
        hash1: np.ndarray,
        hash2: np.ndarray
    ) -> dict:
        """
        Compute similarity between two hashes.
        
        Args:
            hash1: Binary hash [256]
            hash2: Binary hash [256]
        
        Returns:
            {
                'hamming_distance': int (0-256),
                'similarity_score': float (0-1),
                'is_similar': bool,
                'confidence': str ('very_high', 'high', 'medium', 'low', 'very_low')
            }
        """
        # Compute Hamming distance
        hamming_dist = int(np.sum(hash1 != hash2))
        
        # Similarity score (1 = identical, 0 = completely different)
        similarity_score = 1.0 - (hamming_dist / self.config.hash_bits)
        
        # Determine if similar
        is_similar = hamming_dist <= self.config.similarity_threshold
        
        # Confidence level based on v4.0 performance targets
        if hamming_dist <= self.config.very_similar_threshold:
            confidence = "very_high"  # 0-40 bits
        elif hamming_dist <= self.config.similarity_threshold:
            confidence = "high"  # 41-66 bits
        elif hamming_dist <= 100:
            confidence = "medium"  # 67-100 bits
        elif hamming_dist < self.config.dissimilar_threshold:
            confidence = "low"  # 101-119 bits
        else:
            confidence = "very_low"  # 120+ bits
        
        return {
            'hamming_distance': hamming_dist,
            'similarity_score': similarity_score,
            'is_similar': is_similar,
            'confidence': confidence
        }
    
    def get_info(self) -> dict:
        """Get generator information"""
        info = {
            'model_path': str(self.config.hash_model_path),
            'device': self.config.device,
            'feature_dim': self.config.feature_dim,
            'hash_bits': self.config.hash_bits,
            'model_type': 'DeepHash v4.0' if not self.config.use_pca else 'DeepHash with PCA',
            'hidden_dims': self.config.hidden_dims,
            'dropout': self.config.dropout,
            'similarity_threshold': self.config.similarity_threshold
        }
        
        if self.config.use_pca:
            info['pca_path'] = str(self.config.pca_transform_path)
            info['pca_dim'] = self.config.pca_dim
            info['pca_explained_variance'] = f"{self.pca.explained_variance_ratio_.sum():.2%}"
        
        return info
