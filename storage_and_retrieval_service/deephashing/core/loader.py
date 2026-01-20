"""Model loading utilities"""

import torch
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

from .model import DeepHashingHead
from .config import ModelConfig
from ..exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class ModelLoader:
    """Utility class for loading DeepHash models"""
    
    @staticmethod
    def load(
        model_path: Path,
        device: str
    ) -> Tuple[DeepHashingHead, ModelConfig, Dict[str, Any]]:
        """
        Load model from checkpoint.
        
        Args:
            model_path: Path to model checkpoint
            device: Device to load on ('cpu' or 'cuda')
            
        Returns:
            Tuple of (model, config, metrics)
            
        Raises:
            ModelLoadError: If loading fails
        """
        if not model_path.exists():
            raise ModelLoadError(f"Model not found: {model_path}")
        
        try:
            checkpoint = torch.load(
                model_path,
                map_location=device,
                weights_only=False
            )
            
            # Handle state_dict format
            if ModelLoader._is_state_dict_format(checkpoint):
                return ModelLoader._load_from_state_dict(checkpoint, device)
            
            # Handle full model format
            elif 'hash_model' in checkpoint:
                return ModelLoader._load_full_model(checkpoint, 'hash_model')
            
            elif 'model' in checkpoint:
                return ModelLoader._load_full_model(checkpoint, 'model')
            
            else:
                # Direct model object
                return checkpoint, ModelConfig(), {}
                
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {e}") from e
    
    @staticmethod
    def _is_state_dict_format(checkpoint: Dict) -> bool:
        """Check if checkpoint is state_dict format"""
        return (
            isinstance(checkpoint, dict) and
            'state_dict' in checkpoint and
            'hash_model' not in checkpoint
        )
    
    @staticmethod
    def _load_from_state_dict(
        checkpoint: Dict,
        device: str
    ) -> Tuple[DeepHashingHead, ModelConfig, Dict]:
        """Load model from state_dict"""
        logger.info("Loading from state dict...")
        
        # Parse config
        config_dict = checkpoint.get('config', {})
        config = ModelConfig.from_dict(config_dict)
        
        # Reconstruct model
        model = DeepHashingHead(
            input_dim=config.input_dim,
            hash_dim=config.hash_dim,
            hidden_dims=config.hidden_dims
        )
        
        # Load weights
        state_dict = checkpoint['state_dict']
        model.load_state_dict(state_dict, strict=False)
        
        logger.info(f"  Hash dimension: {config.hash_dim}")
        logger.info(f"  Input dimension: {config.input_dim}")
        
        metrics = checkpoint.get('metrics', {})
        
        return model, config, metrics
    
    @staticmethod
    def _load_full_model(
        checkpoint: Dict,
        model_key: str
    ) -> Tuple[DeepHashingHead, ModelConfig, Dict]:
        """Load full model object"""
        logger.info(f"Loading {model_key} object...")
        
        model = checkpoint[model_key]
        config_dict = checkpoint.get('config', {})
        config = ModelConfig.from_dict(config_dict)
        metrics = checkpoint.get('metrics', {})
        
        return model, config, metrics
