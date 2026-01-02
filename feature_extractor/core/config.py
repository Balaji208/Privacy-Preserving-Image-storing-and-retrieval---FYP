"""Configuration classes for feature extraction"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelConfig:
    """Model architecture configuration"""
    model_size: str = 'tiny'
    num_classes: int = 9
    feature_dim: int = 512
    pretrained: bool = False
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'ModelConfig':
        """Create config from dictionary"""
        return cls(
            model_size=config_dict.get('model_size', 'tiny'),
            num_classes=config_dict.get('num_classes', 9),
            feature_dim=config_dict.get('feature_dim', 512),
            pretrained=config_dict.get('pretrained', False)
        )


@dataclass
class ExtractorConfig:
    """Feature extractor configuration"""
    device: Optional[str] = None
    batch_size: int = 32
    normalize: bool = True
    show_progress: bool = False
