"""Model loading utilities"""

import torch
from pathlib import Path
from typing import Tuple
import logging

from .model import ConvNeXtV2FeatureExtractor
from .config import ModelConfig
from ..exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class ModelLoader:
    """Utility for loading ConvNeXt models"""
    
    @staticmethod
    def load(
        model_path: Path,
        device: str
    ) -> Tuple[ConvNeXtV2FeatureExtractor, ModelConfig]:
        """
        Load model from checkpoint.
        
        Args:
            model_path: Path to checkpoint
            device: Device to load on
            
        Returns:
            Tuple of (model, config)
            
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
                return ModelLoader._load_from_state_dict(checkpoint)
            
            # Handle full model format
            elif 'model' in checkpoint:
                return ModelLoader._load_full_model(checkpoint)
            
            else:
                # Direct model object
                return checkpoint, ModelConfig()
                
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {e}") from e
    
    @staticmethod
    def _is_state_dict_format(checkpoint: dict) -> bool:
        """Check if checkpoint is state_dict format"""
        return (
            isinstance(checkpoint, dict) and
            'state_dict' in checkpoint and
            'model' not in checkpoint
        )
    
    @staticmethod
    def _load_from_state_dict(
        checkpoint: dict
    ) -> Tuple[ConvNeXtV2FeatureExtractor, ModelConfig]:
        """Load model from state_dict"""
        logger.info("Loading from state dict...")
        
        # Parse config
        config_dict = checkpoint.get('config', {})
        config = ModelConfig.from_dict(config_dict)
        
        # Reconstruct model
        model = ConvNeXtV2FeatureExtractor(
            model_size=config.model_size,
            num_classes=config.num_classes,
            feature_dim=config.feature_dim,
            pretrained=config.pretrained
        )
        
        # Load weights
        model.load_state_dict(checkpoint['state_dict'])
        
        logger.info(f"  Loaded from state dict")
        
        # Log validation accuracy if available
        if 'best_val_acc' in checkpoint:
            logger.info(f"  Validation accuracy: {checkpoint['best_val_acc']:.4f}")
        
        return model, config
    
    @staticmethod
    def _load_full_model(
        checkpoint: dict
    ) -> Tuple[ConvNeXtV2FeatureExtractor, ModelConfig]:
        """Load full model object"""
        logger.info("Loading model object...")
        
        model = checkpoint['model']
        config_dict = checkpoint.get('config', {})
        config = ModelConfig.from_dict(config_dict)
        
        # Log metadata
        if 'epoch' in checkpoint:
            logger.info(f"  Loaded from epoch {checkpoint['epoch']}")
        if 'best_val_acc' in checkpoint:
            logger.info(f"  Validation accuracy: {checkpoint['best_val_acc']:.4f}")
        
        return model, config
