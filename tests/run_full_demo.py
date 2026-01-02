# run_full_demo.py
from image_encryption.config.kyber_key_setup import setup_kyber_keys
from image_encryption.demo.run_encrypt_demo import main as enc_main
from image_encryption.tests.test_aad_integrity import (
    test_case_1_valid_no_tamper,
    test_case_2_aad_tamper_detected,
    test_case_3_ciphertext_tamper_detected
)


def main():
    print("\n" + "="*80)
    print("🚀 FULL ENCRYPTION + AES-GCM INTEGRITY DEMO")
    print("="*80 + "\n")
    
    # 1) Kyber keys
    print("🔑 STEP 1: Generating Kyber keypair...")
    setup_kyber_keys()
    
    # 2) Encrypt image
    print("\n🔐 STEP 2: Encrypting image...")
    enc_main()
    
    print("\n🧪 STEP 3: Running 3 AES-GCM Tamper Detection Tests...\n")
    
    # 3) Run tests directly (no pytest.main)
    print("📋 TEST CASE 1: VALID (no tampering)")
    test_case_1_valid_no_tamper()
    
    print("\n📋 TEST CASE 2: AAD TAMPER")
    test_case_2_aad_tamper_detected()
    
    print("\n📋 TEST CASE 3: CIPHERTEXT TAMPER")
    test_case_3_ciphertext_tamper_detected()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED! Check output files:")
    print(f"   📸 VALID:        {test_case_1_valid_no_tamper.__globals__['OUT_VALID']}")
    print(f"   🔒 AAD TAMPER:   {test_case_3_ciphertext_tamper_detected.__globals__['OUT_AAD_TAMPER']}")
    print(f"   🔒 CT TAMPER:    {test_case_3_ciphertext_tamper_detected.__globals__['OUT_CT_TAMPER']}")
    print("="*80)


if __name__ == "__main__":
    main()
