"""Image loading utilities"""

from PIL import Image
import numpy as np
from pathlib import Path
from typing import Union

from ..exceptions import ImageLoadError


class ImageLoader:
    """Utility for loading images from various sources"""
    
    @staticmethod
    def load(
        image_input: Union[str, Path, Image.Image, np.ndarray]
    ) -> Image.Image:
        """
        Load image from various input types.
        
        Args:
            image_input: Can be:
                - Path to image file (str or Path)
                - PIL Image object
                - Numpy array (H, W, 3) in RGB format
                
        Returns:
            PIL Image in RGB format
            
        Raises:
            ImageLoadError: If loading fails
        """
        try:
            if isinstance(image_input, (str, Path)):
                return ImageLoader._load_from_path(image_input)
            elif isinstance(image_input, Image.Image):
                return image_input.convert('RGB')
            elif isinstance(image_input, np.ndarray):
                return ImageLoader._load_from_array(image_input)
            else:
                raise ImageLoadError(
                    f"Unsupported input type: {type(image_input)}"
                )
        except Exception as e:
            raise ImageLoadError(f"Failed to load image: {e}") from e
    
    @staticmethod
    def _load_from_path(path: Union[str, Path]) -> Image.Image:
        """Load image from file path"""
        path = Path(path)
        if not path.exists():
            raise ImageLoadError(f"Image not found: {path}")
        return Image.open(path).convert('RGB')
    
    @staticmethod
    def _load_from_array(array: np.ndarray) -> Image.Image:
        """Load image from numpy array"""
        if array.ndim != 3 or array.shape[2] != 3:
            raise ImageLoadError(
                f"Expected array shape (H, W, 3), got {array.shape}"
            )
        return Image.fromarray(array.astype(np.uint8))
