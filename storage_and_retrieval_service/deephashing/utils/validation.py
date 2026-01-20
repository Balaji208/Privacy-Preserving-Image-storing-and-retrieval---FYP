"""Input validation utilities"""

import numpy as np
from typing import Optional
from ..exceptions import ValidationError


class FeatureValidator:
    """Validates input features"""
    
    def __init__(self, expected_dim: int):
        self.expected_dim = expected_dim
    
    def validate(self, features: np.ndarray) -> np.ndarray:
        """
        Validate feature array.
        
        Args:
            features: Input features
            
        Returns:
            Validated features
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(features, np.ndarray):
            raise ValidationError(
                f"Features must be numpy array, got {type(features)}"
            )
        
        if features.ndim not in [1, 2]:
            raise ValidationError(
                f"Features must be 1D or 2D array, got {features.ndim}D"
            )
        
        # Check dimension
        feature_dim = features.shape[-1] if features.ndim == 2 else features.shape[0]
        if feature_dim != self.expected_dim:
            raise ValidationError(
                f"Feature dimension mismatch. "
                f"Expected {self.expected_dim}, got {feature_dim}"
            )
        
        return features
