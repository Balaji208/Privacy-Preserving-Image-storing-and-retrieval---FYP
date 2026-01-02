# image_encryption/utils/image_io.py

from pathlib import Path


def read_image_bytes(image_path: str) -> bytes:
    """
    Read image file as raw bytes

    Args:
        image_path : path to image file

    Returns:
        image bytes
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        return f.read()
