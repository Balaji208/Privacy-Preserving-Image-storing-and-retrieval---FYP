"""Deep hashing model architecture"""

import torch
import torch.nn as nn
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DeepHashingHead(nn.Module):
    """
    Deep Supervised Hashing (DSH) head with advanced features.
    
    Architecture (v4.0 - Research-backed):
        Input (512D or 256D PCA features)
        → Feature layers: [Linear → BatchNorm → ReLU → Dropout] × N
        → Hash layer: Linear(hidden_dim → hash_bits)
    
    Features:
        - Batch normalization for stable training
        - Xavier initialization
        - Dropout for regularization
    
    Args:
        input_dim: Input dimension (512 direct, or 256 after PCA)
        hidden_dims: List of hidden dimensions [1024, 512] or [512, 256]
        hash_bits: Number of hash bits (256)
        dropout: Dropout rate (default: 0.2)
    """
    
    def __init__(
        self,
        input_dim: int = 512,
        hidden_dims: list = None,
        hash_bits: int = 256,
        dropout: float = 0.2
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hash_bits = hash_bits
        
        # Default hidden dims based on input
        if hidden_dims is None:
            if input_dim == 512:
                hidden_dims = [1024, 512]  # v4.0 architecture
            else:
                hidden_dims = [512, 256]   # Legacy architecture
        
        # Build feature layers
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        self.feature_layers = nn.Sequential(*layers)
        
        # Hash layer (outputs continuous hash codes)
        self.hash_layer = nn.Linear(prev_dim, hash_bits)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Xavier initialization for stable training"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, gain=1.0)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input features [batch, input_dim]
        
        Returns:
            Continuous hash codes [batch, hash_bits]
        """
        features = self.feature_layers(x)
        hash_codes = self.hash_layer(features)
        return hash_codes
    
    def get_binary_hash(self, x: torch.Tensor) -> torch.Tensor:
        """
        Generate binary hash codes.
        
        Args:
            x: Input features [batch, input_dim]
        
        Returns:
            Binary hash codes [batch, hash_bits] in {-1, 1}
        """
        self.eval()
        with torch.no_grad():
            hash_codes = self.forward(x)
            return torch.sign(hash_codes)


class DeepHashingModel:
    """
    Wrapper for deep hashing model with optional PCA preprocessing.
    
    Handles two modes:
        1. Direct mode: 512D features → Hash Network → 256-bit codes
        2. PCA mode: 512D features → PCA → 256D → Hash Network → 256-bit codes
    
    Args:
        pca_transform: Fitted sklearn PCA object (None for direct mode)
        hash_model: DeepHashingHead network
        device: Device to run on
        use_pca: Whether to use PCA preprocessing
    """
    
    def __init__(
        self,
        pca_transform,
        hash_model: DeepHashingHead,
        device: str = 'cuda',
        use_pca: bool = True
    ):
        """Initialize model."""
        self.pca = pca_transform
        self.hash_model = hash_model.to(device)
        self.hash_model.eval()
        self.device = device
        self.use_pca = use_pca and (pca_transform is not None)
        
        logger.info("✓ Deep hashing model initialized")
        if self.use_pca:
            logger.info(f"  Mode: PCA preprocessing")
            logger.info(f"  Pipeline: 512D → PCA → {hash_model.input_dim}D → {hash_model.hash_bits}-bit")
        else:
            logger.info(f"  Mode: Direct hashing")
            logger.info(f"  Pipeline: {hash_model.input_dim}D → {hash_model.hash_bits}-bit")
        logger.info(f"  Device: {device}")
    
    def load_weights(self, model_path: str):
        """
        Load model weights from checkpoint.
        
        Supports multiple checkpoint formats:
            1. Direct state_dict (deephash_v4_statedict.pt format) ← YOUR FORMAT
            2. Dict with 'model_state_dict' key
            3. Dict with 'state_dict' key
        
        Args:
            model_path: Path to .pt file
        """
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        try:
            # Load checkpoint
            checkpoint = torch.load(
                model_path,
                map_location=self.device,
                weights_only=False  # Allow unpickling
            )
            
            # Handle different checkpoint formats
            if isinstance(checkpoint, dict):
                # Format 1: Dict with 'model_state_dict' key (full training checkpoint)
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                    logger.info("Detected full training checkpoint format")
                    
                    # Log training metadata if available
                    if 'epoch' in checkpoint:
                        logger.info(f"  Trained for {checkpoint['epoch']} epochs")
                    if 'metrics' in checkpoint:
                        metrics = checkpoint['metrics']
                        if 'hamming_similar' in metrics:
                            logger.info(f"  Similar distance: {metrics['hamming_similar']:.1f} bits")
                        if 'hamming_dissimilar' in metrics:
                            logger.info(f"  Dissimilar distance: {metrics['hamming_dissimilar']:.1f} bits")
                
                # Format 2: Dict with 'state_dict' key
                elif 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                    logger.info("Detected state_dict wrapper format")
                
                # Format 3: Direct state_dict (YOUR v4.0 TRAINING FORMAT)
                else:
                    state_dict = checkpoint
                    logger.info("Detected direct state_dict format (v4.0 optimized training)")
            else:
                raise ValueError(f"Unexpected checkpoint format: {type(checkpoint)}")
            
            # Load weights
            self.hash_model.load_state_dict(state_dict)
            self.hash_model.eval()
            
            logger.info(f"✓ Weights loaded from {model_path.name}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load weights: {e}") from e
    
    @torch.no_grad()
    def generate_hash(
        self,
        features: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Generate hash codes from features.
        
        Args:
            features: Input features [batch, 512] or [512]
        
        Returns:
            Tuple of:
                - binary_hash: Binary codes [batch, hash_bits] in {0, 1}
                - continuous_hash: Continuous codes [batch, hash_bits]
        """
        # Handle single feature vector
        if features.ndim == 1:
            features = features.unsqueeze(0)
        
        # Apply PCA if enabled
        if self.use_pca:
            # Move to numpy for PCA
            if isinstance(features, torch.Tensor):
                features_np = features.cpu().numpy()
            else:
                features_np = features
            
            # Apply PCA whitening
            features_pca = self.pca.transform(features_np)
            
            # Convert back to tensor
            features_tensor = torch.from_numpy(features_pca).float().to(self.device)
        else:
            # Direct mode: use features as-is
            features_tensor = features.to(self.device)
        
        # Generate hash codes
        continuous_hash = self.hash_model(features_tensor)
        
        # Binarize: sign(x) ∈ {-1, 1}, then map to {0, 1}
        binary_hash = (torch.sign(continuous_hash) + 1) / 2
        binary_hash = binary_hash.long()  # {0, 1}
        
        return binary_hash, continuous_hash
    
    def compute_hamming_distance(
        self,
        hash1: torch.Tensor,
        hash2: torch.Tensor
    ) -> int:
        """
        Compute Hamming distance between two binary hashes.
        
        Args:
            hash1: Binary hash [hash_bits]
            hash2: Binary hash [hash_bits]
        
        Returns:
            Hamming distance (0 to hash_bits)
        """
        return (hash1 != hash2).sum().item()
