# image_encryption/demo/run_decrypt_demo.py

import json
from image_encryption.image_decryptor import ImageDecryptor


def main():
    # Load encrypted JSON produced by ImageEncryptor
    with open("image_encryption/data/encrypted_outputs/encrypted_image.json", "r") as f:
        encrypted_object = json.load(f)

    decryptor = ImageDecryptor()
    original_image_bytes = decryptor.decrypt_image(encrypted_object)

    # Save recovered image
    with open("recovered_image.jpg", "wb") as f:
        f.write(original_image_bytes)

    print("✔ Image successfully decrypted and restored as recovered_image.jpg")


if __name__ == "__main__":
    main()
