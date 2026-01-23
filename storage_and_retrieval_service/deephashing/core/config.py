"""Configuration for DeepHashing module"""

from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class DeepHashingConfig:
    """
    Configuration for deep hashing pipeline.
    
    Supports two architectures:
        1. v4.0 (Direct): 512D → [1024, 512] → 256-bit
        2. Legacy (PCA): 512D → PCA(256D) → [512, 256] → 256-bit
    """
    
    # Model paths
    hash_model_path: str  # Path to .pt weights (e.g., deephash_v4_statedict.pt)
    pca_transform_path: Optional[str] = None  # Path to .pkl PCA (None for direct mode)
    
    # Architecture
    feature_dim: int = 512  # Input feature dimension (from ConvNeXt)
    pca_dim: Optional[int] = None  # PCA output dimension (None for direct mode)
    hash_bits: int = 256  # Hash code length
    hidden_dims: Optional[List[int]] = None  # Hidden layer sizes
    dropout: float = 0.2  # Dropout rate
    
    # Mode selection
    use_pca: bool = True  # Whether to use PCA preprocessing
    
    # Inference
    device: str = 'cuda'
    batch_size: int = 256
    
    # Similarity thresholds (Hamming distance)
    similarity_threshold: int = 66  # Similar if distance <= this
    very_similar_threshold: int = 40  # Very similar
    dissimilar_threshold: int = 120  # Dissimilar if distance >= this
    
    def __post_init__(self):
        """Set defaults after initialization"""
        # Determine mode and set defaults
        if self.pca_transform_path is None:
            # Direct mode (v4.0)
            self.use_pca = False
            self.pca_dim = None
            if self.hidden_dims is None:
                self.hidden_dims = [1024, 512]
        else:
            # PCA mode (legacy)
            self.use_pca = True
            if self.pca_dim is None:
                self.pca_dim = 256
            if self.hidden_dims is None:
                self.hidden_dims = [512, 256]
    
    @property
    def model_input_dim(self) -> int:
        """Get model input dimension"""
        if self.use_pca and self.pca_dim is not None:
            return self.pca_dim
        return self.feature_dim
    
    def get_info(self) -> dict:
        """Get configuration info"""
        return {
            'mode': 'PCA' if self.use_pca else 'Direct',
            'feature_dim': self.feature_dim,
            'pca_dim': self.pca_dim,
            'model_input_dim': self.model_input_dim,
            'hash_bits': self.hash_bits,
            'hidden_dims': self.hidden_dims,
            'dropout': self.dropout,
            'device': self.device,
            'similarity_threshold': self.similarity_threshold
        }
