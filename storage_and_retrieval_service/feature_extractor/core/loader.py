"""Model loading utilities"""

import torch
import sys
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
        
        Supports 3 formats:
        1. Direct state_dict (convnextv2_best_phase1.pt format)
        2. Dict with 'state_dict' key
        3. Dict with 'model' key (full model object)
        
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
            # CRITICAL FIX: Make class available for unpickling
            if '__main__' in sys.modules:
                sys.modules['__main__'].ConvNeXtV2FeatureExtractor = ConvNeXtV2FeatureExtractor
            
            checkpoint = torch.load(
                model_path,
                map_location=device,
                weights_only=False
            )
            
            # Handle different checkpoint formats
            if isinstance(checkpoint, dict):
                # Format 1: Dict with 'state_dict' key
                if 'state_dict' in checkpoint:
                    return ModelLoader._load_from_dict_state_dict(checkpoint, device)
                # Format 2: Dict with 'model' key (full model object)
                elif 'model' in checkpoint:
                    return ModelLoader._load_full_model(checkpoint)
                # Format 3: Direct state_dict (e.g., OrderedDict from torch.save(model.state_dict()))
                else:
                    return ModelLoader._load_direct_state_dict(checkpoint, device)
            else:
                # Assume it's a model object directly
                logger.info("Loading direct model object...")
                return checkpoint, ModelConfig()
                
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {e}") from e
    
    @staticmethod
    def _load_direct_state_dict(
        state_dict: dict,
        device: str
    ) -> Tuple[ConvNeXtV2FeatureExtractor, ModelConfig]:
        """
        Load from direct state_dict format (convnextv2_best_phase1.pt).
        
        This is the format saved by: torch.save(model.state_dict(), path)
        """
        logger.info("Detected direct state_dict format (Phase 1 model)")
        
        # Use default config (Phase 1 model specs)
        config = ModelConfig(
            model_size='tiny',
            num_classes=9,
            feature_dim=512,
            pretrained=False
        )
        
        # Reconstruct model
        model = ConvNeXtV2FeatureExtractor(
            model_size=config.model_size,
            num_classes=config.num_classes,
            feature_dim=config.feature_dim,
            pretrained=config.pretrained
        )
        
        # Load weights
        model.load_state_dict(state_dict)
        model.to(device)
        
        logger.info(f"✓ Loaded Phase 1 diversity model")
        logger.info(f"✓ Feature dim: {config.feature_dim}")
        logger.info(f"✓ Model size: {config.model_size}")
        
        return model, config
    
    @staticmethod
    def _load_from_dict_state_dict(
        checkpoint: dict,
        device: str
    ) -> Tuple[ConvNeXtV2FeatureExtractor, ModelConfig]:
        """Load model from dict containing state_dict"""
        logger.info("Loading from dict with state_dict key...")
        
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
        model.to(device)
        
        logger.info(f"✓ Loaded from state dict")
        
        # Log validation accuracy if available
        if 'best_val_acc' in checkpoint:
            logger.info(f"✓ Validation accuracy: {checkpoint['best_val_acc']:.4f}")
        
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
            logger.info(f"✓ Loaded from epoch {checkpoint['epoch']}")
        if 'best_val_acc' in checkpoint:
            logger.info(f"✓ Validation accuracy: {checkpoint['best_val_acc']:.4f}")
        
        return model, config
