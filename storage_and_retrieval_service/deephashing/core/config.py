"""Configuration dataclass for DeepHash models"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ModelConfig:
    """Model configuration"""
    input_dim: int = 512
    hash_dim: int = 256
    hidden_dims: list = field(default_factory=lambda: [512, 512])
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ModelConfig':
        """Create config from dictionary"""
        return cls(
            input_dim=config_dict.get('input_dim', 512),
            hash_dim=config_dict.get('hash_dim', 256),
            hidden_dims=config_dict.get('hidden_dims', [512, 512])
        )


@dataclass
class GeneratorConfig:
    """Generator configuration"""
    device: Optional[str] = None
    batch_size: int = 256
    show_progress: bool = False
