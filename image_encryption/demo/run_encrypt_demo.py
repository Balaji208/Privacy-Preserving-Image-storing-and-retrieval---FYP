import json
from pathlib import Path

from image_encryption.image_encryptor import ImageEncryptor
from image_encryption.utils.image_io import read_image_bytes


def main():
    encryptor = ImageEncryptor()

    image_bytes = read_image_bytes(
        "image_encryption/data/input_images/sample.jpg"
    )

    enc = encryptor.encrypt_image(
        image_bytes=image_bytes,
        image_id="img123",
        user_id="user1",
        timestamp="2025-01-01T10:00:00",
    )

    # Ensure output directory exists
    output_dir = Path("image_encryption/data/encrypted_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "encrypted_image.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enc, f, indent=2)

    print(f"Encrypted JSON written to {output_path}")


if __name__ == "__main__":
    main()
