from image_encryption.config.kyber_key_setup import setup_kyber_keys
from image_encryption.demo.run_encrypt_demo import main as enc_main
from image_encryption.demo.run_decrypt_demo import main as dec_main

if __name__ == "__main__":
    setup_kyber_keys()
    enc_main()
    dec_main()
