"""Main feature extraction API"""

import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import Union, List, Optional
import logging
from PIL import Image

from .core.loader import ModelLoader
from .core.config import ExtractorConfig
from .preprocessing.transforms import ImageTransforms
from .preprocessing.image_loader import ImageLoader
from .exceptions import FeatureExtractionError

logger = logging.getLogger(__name__)


class ConvNeXtFeatureExtractor:
    """
    ConvNeXt-V2 feature extractor.
    Extracts 512-D L2-normalized features from images.
    
    Args:
        model_path: Path to model checkpoint (supports convnextv2_best_phase1.pt)
        device: Device ('cuda' or 'cpu'). Auto-detects if None
        batch_size: Batch size for processing (default: 32)
    
    Example:
        >>> extractor = ConvNeXtFeatureExtractor('models/convnextv2_best_phase1.pt')
        >>> features = extractor.extract('image.jpg')
        >>> print(features.shape)  # (512,)
    """
    
    def __init__(
        self,
        model_path: Union[str, Path],
        device: Optional[str] = None,
        batch_size: int = 32
    ):
        self.model_path = Path(model_path)
        self.config = ExtractorConfig(device=device, batch_size=batch_size)
        
        # Setup device
        if self.config.device is None:
            self.config.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Load model
        logger.info(f"Loading model from: {self.model_path}")
        self.model, self.model_config = ModelLoader.load(
            self.model_path,
            self.config.device
        )
        
        self.model.eval()
        self.model.to(self.config.device)
        
        # Setup utilities
        self.feature_dim = self._detect_feature_dim()
        self.transform = ImageTransforms.get_inference_transform()
        self.image_loader = ImageLoader()
        
        self._log_info()
    
    def _detect_feature_dim(self) -> int:
        """Detect output feature dimension"""
        with torch.no_grad():
            dummy = torch.randn(1, 3, 224, 224).to(self.config.device)
            features = self.model(dummy, return_features=True)
            return features.shape[1]
    
    def _log_info(self):
        """Log model information"""
        logger.info(f"✓ Model loaded on {self.config.device}")
        logger.info(f"✓ Feature dimension: {self.feature_dim}")
        logger.info(f"✓ Model type: ConvNeXt-V2 {self.model_config.model_size}")
        logger.info(f"✓ Batch size: {self.config.batch_size}")
    
    @torch.no_grad()
    def extract(
        self,
        image: Union[str, Path, Image.Image, np.ndarray],
        normalize: bool = True
    ) -> np.ndarray:
        """
        Extract features from single image.
        
        Args:
            image: Input image (path, PIL Image, or numpy array)
            normalize: Apply L2 normalization (default: True)
        
        Returns:
            Feature vector of shape (512,)
        """
        try:
            # Load and preprocess
            pil_image = self.image_loader.load(image)
            img_tensor = self.transform(pil_image).unsqueeze(0).to(self.config.device)
            
            # Extract features
            features = self.model(img_tensor, return_features=True)
            
            # Normalize
            if normalize:
                features = F.normalize(features, p=2, dim=1)
            
            return features.cpu().numpy()[0]
        
        except Exception as e:
            raise FeatureExtractionError(
                f"Failed to extract features: {e}"
            ) from e
    
    @torch.no_grad()
    def extract_batch(
        self,
        images: List[Union[str, Path, Image.Image, np.ndarray]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Extract features from multiple images.
        
        Args:
            images: List of images
            normalize: Apply L2 normalization (default: True)
            show_progress: Show progress bar (default: False)
        
        Returns:
            Feature matrix of shape (num_images, 512)
        """
        all_features = []
        
        # Optional progress bar
        iterator = range(0, len(images), self.config.batch_size)
        if show_progress:
            try:
                from tqdm.auto import tqdm
                iterator = tqdm(iterator, desc='Extracting features')
            except ImportError:
                pass
        
        # Process in batches
        for i in iterator:
            batch = images[i:i + self.config.batch_size]
            
            # Load and preprocess
            tensors = []
            for img in batch:
                pil_image = self.image_loader.load(img)
                tensor = self.transform(pil_image)
                tensors.append(tensor)
            
            batch_tensor = torch.stack(tensors).to(self.config.device)
            
            # Extract features
            batch_features = self.model(batch_tensor, return_features=True)
            
            # Normalize
            if normalize:
                batch_features = F.normalize(batch_features, p=2, dim=1)
            
            all_features.append(batch_features.cpu().numpy())
        
        return np.concatenate(all_features, axis=0)
    
    def get_info(self) -> dict:
        """Get extractor information"""
        return {
            'model_path': str(self.model_path),
            'device': self.config.device,
            'feature_dim': self.feature_dim,
            'batch_size': self.config.batch_size,
            'model_type': 'ConvNeXt-V2',
            'model_size': self.model_config.model_size,
            'num_classes': self.model_config.num_classes
        }
