# image_encryption/evaluation/metrics_eval.py

import os
import time
import math
import statistics

from image_encryption.crypto.aes_gcm import AESGCMEncryptor
from image_encryption.crypto.csprng import CSPRNG
from image_encryption.crypto.kyber_kem import KyberKEM
from image_encryption.crypto.hkdf_kek import HKDFKEK
from image_encryption.crypto.cek_wrap import CEKWrapper
from image_encryption.utils.image_io import read_image_bytes  # real images support


# ----------------------------------------------------------------------
# Helper: basic image loss metrics
# ----------------------------------------------------------------------


def byte_mse(x: bytes, y: bytes) -> float:
    """Mean squared error between two byte arrays."""
    assert len(x) == len(y)
    s = 0
    for a, b in zip(x, y):
        d = a - b
        s += d * d
    return s / len(x)


def byte_psnr(x: bytes, y: bytes, max_val: int = 255) -> float:
    """PSNR in dB for byte arrays (treat bytes as grayscale pixels)."""
    mse = byte_mse(x, y)
    if mse == 0:
        return float("inf")
    return 10.0 * math.log10((max_val * max_val) / mse)


def bit_error_rate(x: bytes, y: bytes) -> float:
    """Bit error rate (fraction of flipped bits)."""
    assert len(x) == len(y)
    diff_bits = 0
    total_bits = len(x) * 8
    for a, b in zip(x, y):
        diff_bits += (a ^ b).bit_count()
    return diff_bits / total_bits


# ----------------------------------------------------------------------
# Encryption/decryption pipelines
# ----------------------------------------------------------------------


def encrypt_image_pipeline(plaintext: bytes) -> dict:
    # 1) Kyber key pair (receiver side)
    kp = KyberKEM.generate_keypair()
    public_key = kp["public_key"]
    secret_key = kp["secret_key"]

    # 2) KEM encapsulation (sender side)
    enc = KyberKEM.encapsulate(public_key)
    ct_kem = enc["ciphertext"]
    shared_secret = enc["shared_secret"]

    # 3) HKDF to derive KEK
    salt = CSPRNG.generate_salt(32)
    info = b"CEK-WRAPPING-KEY"
    kek = HKDFKEK.derive_kek(shared_secret, salt, info)

    # 4) Generate CEK and wrap it with KEK (AES-GCM)
    cek = CSPRNG.generate_cek()
    aad_cek = b"CEK-WRAPPING"
    wrap_info = CEKWrapper.wrap_cek(cek, kek, aad_cek)

    wrapped_cek = wrap_info["wrapped_cek"]   # bytes
    nonce_cek = wrap_info["nonce"]           # bytes
    tag_cek = wrap_info["tag"]               # bytes

    # 5) Encrypt image with CEK (AES-GCM)
    nonce_img = CSPRNG.generate_nonce()
    img_aad_dict = {
        "img_id": "test-image",
        "timestamp": "2025-01-01T00:00:00Z",
        "user_id": "test-user",
    }
    enc_img = AESGCMEncryptor.encrypt(
        plaintext_bytes=plaintext,
        cek=cek,
        nonce=nonce_img,
        aad_dict=img_aad_dict,
    )

    ciphertext = enc_img["ciphertext"]
    tag_img = enc_img["auth_tag"]

    return {
        "ciphertext": ciphertext,
        "tag_img": tag_img,
        "nonce_img": enc_img["nonce"],
        "aad_img": enc_img["aad"],  # this is the dict
        "kem_ct": ct_kem,
        "shared_secret": shared_secret,
        "secret_key": secret_key,
        "salt": salt,
        "wrapped_cek": wrapped_cek,
        "nonce_cek": nonce_cek,
        "tag_cek": tag_cek,
        "plaintext_len": len(plaintext),
    }


def decrypt_image_pipeline(bundle: dict) -> bytes:
    # 1) Kyber decapsulation (receiver side)
    shared_secret = KyberKEM.decapsulate(
        ciphertext=bundle["kem_ct"],
        secret_key=bundle["secret_key"],
    )

    # 2) Derive KEK again with HKDF
    kek = HKDFKEK.derive_kek(shared_secret, bundle["salt"], b"CEK-WRAPPING-KEY")

    # 3) Unwrap CEK
    aad_cek = b"CEK-WRAPPING"
    cek = CEKWrapper.unwrap_cek(
        wrapped_cek=bundle["wrapped_cek"],  # bytes
        nonce=bundle["nonce_cek"],          # bytes
        tag=bundle["tag_cek"],              # bytes
        kek=kek,
        aad=aad_cek,
    )

    # 4) Decrypt image
    plaintext = AESGCMEncryptor.decrypt(
        ciphertext=bundle["ciphertext"],
        auth_tag=bundle["tag_img"],
        cek=cek,
        nonce=bundle["nonce_img"],
        aad_dict=bundle["aad_img"],
    )
    return plaintext


# ----------------------------------------------------------------------
# Pretty printing helpers
# ----------------------------------------------------------------------


def print_section_title(title: str):
    line = "=" * len(title)
    print(f"\n{line}\n{title}\n{line}")


def print_table(rows, headers):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cols):
        return " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cols))

    sep = "-+-".join("-" * w for w in col_widths)

    print(fmt_row(headers))
    print(sep)
    for row in rows:
        print(fmt_row(row))


def ascii_hist(values, bins=10, width=40):
    if not values:
        return
    vmin, vmax = min(values), max(values)
    if vmin == vmax:
        print(f"[{vmin:.3f}] " + "#" * (width // 2))
        return

    step = (vmax - vmin) / bins if bins > 0 else (vmax - vmin)
    if step == 0:
        print(f"[{vmin:.3f}] " + "#" * (width // 2))
        return

    bucket_counts = [0] * bins
    for v in values:
        idx = min(int((v - vmin) / step), bins - 1)
        bucket_counts[idx] += 1

    max_cnt = max(bucket_counts) if bucket_counts else 0
    for i, cnt in enumerate(bucket_counts):
        bar_len = int(width * (cnt / max_cnt)) if max_cnt else 0
        start = vmin + i * step
        end = start + step
        print(f"{start:8.3f}–{end:8.3f}: " + "#" * bar_len)


# ----------------------------------------------------------------------
# Metrics runner
# ----------------------------------------------------------------------


def run_metrics(
    num_runs: int = 20,
    img_size_bytes: int = 256 * 1024,
    image_path: str | None = None,
):
    enc_times = []
    dec_times = []
    expansions = []
    mses = []
    psnrs = []
    bers = []
    failures = 0

    print_section_title("POST-QUANTUM IMAGE ENCRYPTION METRICS")

    for i in range(num_runs):
        if image_path is not None:
            plaintext = read_image_bytes(image_path)
        else:
            plaintext = os.urandom(img_size_bytes)

        # encrypt
        t0 = time.perf_counter()
        bundle = encrypt_image_pipeline(plaintext)
        t1 = time.perf_counter()

        # decrypt
        t2 = time.perf_counter()
        decrypted = decrypt_image_pipeline(bundle)
        t3 = time.perf_counter()

        # correctness
        if decrypted != plaintext:
            failures += 1

        enc_time = (t1 - t0) * 1000.0
        dec_time = (t3 - t2) * 1000.0

        enc_times.append(enc_time)
        dec_times.append(dec_time)

        total_cipher_bytes = len(bundle["ciphertext"])
        expansion = total_cipher_bytes / bundle["plaintext_len"]
        expansions.append(expansion)

        mse = byte_mse(plaintext, decrypted)
        psnr = byte_psnr(plaintext, decrypted)
        ber = bit_error_rate(plaintext, decrypted)
        mses.append(mse)
        psnrs.append(psnr)
        bers.append(ber)

        print(
            f"Run {i+1:02d}/{num_runs}: "
            f"enc={enc_time:7.3f} ms | "
            f"dec={dec_time:7.3f} ms | "
            f"exp={expansion:5.3f} | "
            f"MSE={mse:.6f} | PSNR={psnr:6.2f} dB | BER={ber:.6e}"
        )

    def stats(values):
        return {
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }

    enc_stats = stats(enc_times)
    dec_stats = stats(dec_times)
    exp_stats = stats(expansions)
    mse_stats = stats(mses)
    ber_stats = stats(bers)

    finite_psnrs = [p for p in psnrs if math.isfinite(p)]
    if finite_psnrs:
        psnr_stats = stats(finite_psnrs)
    else:
        psnr_stats = {"avg": float("inf"), "min": float("inf"), "max": float("inf")}

    print_section_title("SUMMARY TABLE")

    rows = [
        ["Runs", num_runs],
        ["Failures", failures],
        [
            "Enc time (ms) avg/min/max",
            f"{enc_stats['avg']:.3f} / {enc_stats['min']:.3f} / {enc_stats['max']:.3f}",
        ],
        [
            "Dec time (ms) avg/min/max",
            f"{dec_stats['avg']:.3f} / {dec_stats['min']:.3f} / {dec_stats['max']:.3f}",
        ],
        [
            "Expansion (cipher/plain)",
            f"{exp_stats['avg']:.4f} avg",
        ],
        [
            "MSE avg/min/max",
            f"{mse_stats['avg']:.6f} / {mse_stats['min']:.6f} / {mse_stats['max']:.6f}",
        ],
        [
            "PSNR avg/min/max (dB)",
            f"{psnr_stats['avg']:.2f} / {psnr_stats['min']:.2f} / {psnr_stats['max']:.2f}",
        ],
        [
            "BER avg/min/max",
            f"{ber_stats['avg']:.3e} / {ber_stats['min']:.3e} / {ber_stats['max']:.3e}",
        ],
    ]

    print_table(rows, headers=["Metric", "Value"])

    print_section_title("ENC/DEC TIME HISTOGRAM (ms)")
    print("Encryption time:")
    ascii_hist(enc_times, bins=10, width=40)
    print("\nDecryption time:")
    ascii_hist(dec_times, bins=10, width=40)

    print_section_title("LOSS HISTOGRAMS")
    print("MSE:")
    ascii_hist(mses, bins=10, width=40)
    print("\nPSNR (dB):")
    ascii_hist(psnrs, bins=10, width=40)
    print("\nBER:")
    ascii_hist(bers, bins=10, width=40)


if __name__ == "__main__":
    # Real image example
    run_metrics(
        num_runs=10,
        image_path="image_encryption/data/input_images/sample.jpg",
    )
    # Or, for synthetic data:
    # run_metrics(num_runs=20, img_size_bytes=256 * 1024, image_path=None)
