import json
import base64
import io

from PIL import Image
import matplotlib.pyplot as plt


def show_cipher_image(json_path: str):
    # 1) Load encrypted JSON
    with open(json_path, "r", encoding="utf-8") as f:
        enc_obj = json.load(f)

    # 2) Decode the Base64 ciphertext bytes
    #    Adjust key if your field name is different
    image_ciphertext_b64 = enc_obj["image_ciphertext"]
    image_ciphertext = base64.b64decode(image_ciphertext_b64)

    # 3) Choose image dimensions and mode
    #    If you know original width/height, use them.
    #    Example for 256x256 grayscale:
    width = 256
    height = 256
    mode = "L"  # grayscale

    if len(image_ciphertext) < width * height:
        raise ValueError("Ciphertext shorter than width*height; adjust dimensions.")

    # 4) Take first width*height bytes and build an image
    pixel_data = image_ciphertext[: width * height]

    img = Image.frombytes(mode, (width, height), pixel_data)

    # 5) Show using matplotlib
    plt.imshow(img, cmap="gray")
    plt.axis("off")
    plt.title("Cipher Image (byte values as pixels)")
    plt.show()


if __name__ == "__main__":
    show_cipher_image("image_encryption/data/encrypted_outputs/encrypted_image.json")
