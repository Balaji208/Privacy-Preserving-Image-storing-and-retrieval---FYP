"""Image transformation pipelines"""

from torchvision import transforms


class ImageTransforms:
    """Standard image transformations for ConvNeXt"""
    
    # ImageNet normalization parameters
    IMAGENET_MEAN = [0.485, 0.456, 0.406]
    IMAGENET_STD = [0.229, 0.224, 0.225]
    
    @staticmethod
    def get_inference_transform() -> transforms.Compose:
        """
        Get standard inference transform.
        
        Returns:
            Compose pipeline with:
                - Resize to 256
                - Center crop to 224
                - Convert to tensor
                - ImageNet normalization
        """
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=ImageTransforms.IMAGENET_MEAN,
                std=ImageTransforms.IMAGENET_STD
            )
        ])
    
    @staticmethod
    def get_training_transform() -> transforms.Compose:
        """Get training transform with augmentation"""
        return transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=ImageTransforms.IMAGENET_MEAN,
                std=ImageTransforms.IMAGENET_STD
            )
        ])
