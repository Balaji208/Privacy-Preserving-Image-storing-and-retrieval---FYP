"""Main DeepHash generator API"""

import torch
import numpy as np
from pathlib import Path
from typing import Union, Tuple, Optional
import logging

from .core.loader import ModelLoader
from .core.config import GeneratorConfig
from .utils.validation import FeatureValidator
from .utils.metrics import HashMetrics
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class DeepHashGenerator:
    """
    DeepHash binary code generator.
    
    Args:
        model_path: Path to model checkpoint
        device: Device ('cuda' or 'cpu'). Auto-detects if None
        batch_size: Batch size for processing (default: 256)
        
    Example:
        >>> generator = DeepHashGenerator('models/deephash.pt')
        >>> features = np.random.randn(512)
        >>> hash_code = generator.generate(features)
        >>> print(hash_code.shape)  # (256,)
    """
    
    def __init__(
        self,
        model_path: Union[str, Path],
        device: Optional[str] = None,
        batch_size: int = 256
    ):
        self.model_path = Path(model_path)
        self.config = GeneratorConfig(device=device, batch_size=batch_size)
        
        # Setup device
        if self.config.device is None:
            self.config.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Load model
        logger.info(f"Loading model from: {self.model_path}")
        self.model, self.model_config, self.metrics = ModelLoader.load(
            self.model_path,
            self.config.device
        )
        self.model.eval()
        self.model.to(self.config.device)
        
        # Setup utilities
        self.hash_bits = self._get_hash_bits()
        self.input_dim = self._get_input_dim()
        self.validator = FeatureValidator(self.input_dim)
        self.metrics_calc = HashMetrics(self.hash_bits)
        
        self._log_info()
    
    def _get_hash_bits(self) -> int:
        """Get hash dimension from model"""
        if hasattr(self.model, 'hash_bits'):
            return self.model.hash_bits
        elif hasattr(self.model, 'hash_dim'):
            return self.model.hash_dim
        else:
            return self.model_config.hash_dim
    
    def _get_input_dim(self) -> int:
        """Get input dimension from model"""
        if hasattr(self.model, 'input_dim'):
            return self.model.input_dim
        else:
            return self.model_config.input_dim
    
    def _log_info(self):
        """Log model information"""
        logger.info(f"✓ Model loaded on {self.config.device}")
        logger.info(f"✓ Hash bits: {self.hash_bits}")
        logger.info(f"✓ Input dimension: {self.input_dim}")
        if self.metrics and 'map' in self.metrics:
            logger.info(f"✓ Model mAP: {self.metrics['map']:.4f}")
    
    @torch.no_grad()
    def generate(
        self,
        features: np.ndarray,
        return_logits: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """
        Generate hash code from features.
        
        Args:
            features: Feature vector (D,) or batch (N, D)
            return_logits: Return raw logits if True
            
        Returns:
            Binary hash code(s)
        """
        # Validate
        features = self.validator.validate(features)
        
        # Ensure 2D
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Convert to tensor
        features_tensor = torch.from_numpy(features).float().to(self.config.device)
        
        # Generate hashes
        hash_codes = self._generate_hash_codes(features_tensor)
        
        # Convert to numpy
        hash_codes = hash_codes.cpu().numpy()
        
        if return_logits:
            logits = self.model(features_tensor).cpu().numpy()
            return hash_codes, logits
        
        return hash_codes.squeeze()
    
    @torch.no_grad()
    def generate_batch(
        self,
        features: np.ndarray,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate hash codes for batch.
        
        Args:
            features: Feature matrix (N, D)
            show_progress: Show progress bar
            
        Returns:
            Binary hash codes (N, hash_bits)
        """
        # Validate
        features = self.validator.validate(features)
        
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        num_samples = features.shape[0]
        all_hashes = []
        
        # Optional progress bar
        iterator = range(0, num_samples, self.config.batch_size)
        if show_progress and num_samples > 1000:
            try:
                from tqdm.auto import tqdm
                iterator = tqdm(iterator, desc='Generating hashes')
            except ImportError:
                pass
        
        # Process in batches
        for i in iterator:
            batch = features[i:i + self.config.batch_size]
            batch_tensor = torch.from_numpy(batch).float().to(self.config.device)
            batch_hashes = self._generate_hash_codes(batch_tensor)
            all_hashes.append(batch_hashes.cpu().numpy())
        
        return np.concatenate(all_hashes, axis=0)
    
    def _generate_hash_codes(self, features_tensor: torch.Tensor) -> torch.Tensor:
        """Internal method to generate hash codes"""
        if hasattr(self.model, 'generate_hash'):
            return self.model.generate_hash(features_tensor)
        elif hasattr(self.model, 'get_binary_codes'):
            return self.model.get_binary_codes(features_tensor)
        else:
            # Manual generation
            logits = self.model(features_tensor)
            hash_codes = torch.sign(logits)
            hash_codes = (hash_codes + 1) / 2
            return hash_codes.int()
    
    def compute_hamming_distance(
        self,
        codes1: np.ndarray,
        codes2: np.ndarray
    ) -> Union[int, np.ndarray]:
        """Compute Hamming distance between codes"""
        return self.metrics_calc.hamming_distance(codes1, codes2)
    
    def compute_similarity(
        self,
        codes1: np.ndarray,
        codes2: np.ndarray
    ) -> Union[float, np.ndarray]:
        """Compute similarity score"""
        return self.metrics_calc.similarity(codes1, codes2)
    
    def get_info(self) -> dict:
        """Get generator information"""
        info = {
            'model_path': str(self.model_path),
            'device': self.config.device,
            'hash_bits': self.hash_bits,
            'input_dim': self.input_dim,
            'batch_size': self.config.batch_size,
            'model_type': 'DeepHash'
        }
        
        if self.metrics:
            info['metrics'] = self.metrics
        
        return info
