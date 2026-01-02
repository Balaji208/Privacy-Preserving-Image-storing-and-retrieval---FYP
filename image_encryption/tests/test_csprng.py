# tests/test_csprng.py

from crypto.csprng import CSPRNG

cek1 = CSPRNG.generate_cek()
cek2 = CSPRNG.generate_cek()

nonce = CSPRNG.generate_nonce()
salt = CSPRNG.generate_salt()

print("CEK length:", len(cek1))
print("CEKs equal?", cek1 == cek2)
print("Nonce length:", len(nonce))
print("Salt length:", len(salt))
