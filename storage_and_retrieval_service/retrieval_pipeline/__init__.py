"""
Retrieval Pipeline Module
=========================

Decrypts images from similarity search results.

Flow:
1. Send query to similarity search service
2. Receive array of JSON objects (encrypted image data)
3. Decrypt images using Kyber + AES-GCM
4. Save to local filesystem

Components:
- BatchDecryptor: Parallel image decryption
- ImageSaver: Save images to retrieved_images/
- Pipeline: Orchestrate the entire flow
"""

from .pipeline import RetrievalPipeline
from .batch_decryptor import BatchDecryptor
from .image_saver import ImageSaver

__all__ = [
    'RetrievalPipeline',
    'BatchDecryptor',
    'ImageSaver'
]
