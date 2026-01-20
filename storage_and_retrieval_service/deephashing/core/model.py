"""DeepHashing model architecture"""

import torch
import torch.nn as nn
from typing import Optional


class DeepHashingHead(nn.Module):
    """
    DeepHashing network for generating binary hash codes.
    
    Architecture: Linear(512→256) + BatchNorm1d(256)
    
    Args:
        input_dim: Input feature dimension (default: 512)
        hash_dim: Output hash dimension (default: 256)
        hidden_dims: Not used, kept for API compatibility
    """
    
    def __init__(
        self,
        input_dim: int = 512,
        hash_dim: int = 256,
        hidden_dims: Optional[list] = None
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hash_dim = hash_dim
        
        # Simple architecture: Linear + BatchNorm
        self.hash_layer = nn.Sequential(
            nn.Linear(input_dim, hash_dim),
            nn.BatchNorm1d(hash_dim)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input features [batch_size, input_dim]
            
        Returns:
            Hash logits [batch_size, hash_dim]
        """
        return self.hash_layer(x)
    
    @torch.no_grad()
    def generate_hash(self, x: torch.Tensor) -> torch.Tensor:
        """
        Generate binary hash codes.
        
        Args:
            x: Input features [batch_size, input_dim]
            
        Returns:
            Binary codes [batch_size, hash_dim] in {0, 1}
        """
        logits = self.forward(x)
        hash_codes = torch.sign(logits)
        hash_codes = (hash_codes + 1) / 2
        return hash_codes.int()
