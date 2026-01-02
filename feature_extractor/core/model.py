"""ConvNeXt-V2 model architecture"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from typing import Optional


class ConvNeXtV2FeatureExtractor(nn.Module):
    """
    ConvNeXt-V2 feature extraction model.
    
    Architecture:
        - ConvNeXt-V2 backbone (from timm)
        - Projection head: Linear → LayerNorm → GELU
        - Classification head (optional)
    
    Args:
        model_size: Size of ConvNeXt ('tiny', 'base', etc.)
        num_classes: Number of output classes
        feature_dim: Dimension of feature vector (default: 512)
        pretrained: Load pretrained weights (default: False)
    """
    
    def __init__(
        self,
        model_size: str = 'tiny',
        num_classes: int = 9,
        feature_dim: int = 512,
        pretrained: bool = False
    ):
        super().__init__()
        
        self.model_size = model_size
        self.num_classes = num_classes
        self.feature_dim = feature_dim
        
        # Backbone
        model_name = f'convnextv2_{model_size}.fcmae_ft_in22k_in1k'
        self.backbone = timm.create_model(
            model_name,
            pretrained=pretrained,
            num_classes=0  # Remove classification head
        )
        
        # Get backbone output dimension
        backbone_dim = self._get_backbone_dim()
        
        # Projection head
        self.projection = nn.Sequential(
            nn.Linear(backbone_dim, feature_dim),
            nn.LayerNorm(feature_dim),
            nn.GELU()
        )
        
        # Classification head
        self.classifier = nn.Linear(feature_dim, num_classes)
    
    def _get_backbone_dim(self) -> int:
        """Get backbone output dimension"""
        with torch.no_grad():
            dummy_input = torch.randn(1, 3, 224, 224)
            return self.backbone(dummy_input).shape[1]
    
    def forward(
        self,
        x: torch.Tensor,
        return_features: bool = False
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor [batch_size, 3, 224, 224]
            return_features: Return features instead of logits
            
        Returns:
            Features [batch_size, feature_dim] if return_features=True,
            else logits [batch_size, num_classes]
        """
        # Extract features
        x = self.backbone(x)
        features = self.projection(x)
        features = F.normalize(features, p=2, dim=1)
        
        if return_features:
            return features
        
        # Classification
        logits = self.classifier(features)
        return logits
