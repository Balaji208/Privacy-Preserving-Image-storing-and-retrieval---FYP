# hsm/key_store.py

from hsm.hsm_manager import get_hsm_manager

class KeyStore:
    """
    High-level abstraction for HSM key storage.
    
    Provides methods to store and retrieve system-wide cryptographic keys:
    - Kyber secret key (for PQC image encryption)
    - LSH HMAC key (for similarity search)
    """
    
    def __init__(self):
        self.hsm = get_hsm_manager()
    
    def store_kyber_secret_key(self, sk: bytes):
        """
        Store system-wide Kyber secret key in HSM.
        
        Args:
            sk: Kyber-768 secret key bytes (2400 bytes)
        
        Note:
            This key is shared across the entire system for all image encryptions.
        """
        if len(sk) != 2400:
            raise ValueError(f"Invalid Kyber-768 secret key size: {len(sk)} bytes (expected 2400)")
        
        print(f"[KeyStore] Storing Kyber SK in HSM (size: {len(sk)} bytes)")
        
        # Delete existing key if present
        try:
            self.hsm.delete_secret("KYBER_SECRET_KEY")
            print("[KeyStore]   ✓ Deleted existing KYBER_SECRET_KEY")
        except ValueError:
            pass  # Key doesn't exist
        except Exception as e:
            print(f"[KeyStore]   ⚠ Warning during delete: {e}")
        
        # Store with proper label
        try:
            self.hsm.store_secret_test("KYBER_SECRET_KEY", sk)
            print(f"[KeyStore]   ✓ Stored: KYBER_SECRET_KEY ({len(sk)} bytes)")
        except Exception as e:
            print(f"[KeyStore]   ✗ FAILED to store key: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def load_kyber_secret_key(self) -> bytes:
        """
        Load system-wide Kyber secret key from HSM.
        
        Returns:
            Kyber-768 secret key bytes (2400 bytes)
        
        Raises:
            ValueError: If key not found in HSM
        """
        try:
            sk = self.hsm.retrieve_secret("KYBER_SECRET_KEY")
            
            if len(sk) != 2400:
                raise ValueError(f"Invalid Kyber SK size retrieved: {len(sk)} bytes")
            
            return sk
        except Exception as e:
            print(f"[KeyStore] ✗ Failed to load Kyber SK: {e}")
            raise
    
    def kyber_key_exists(self) -> bool:
        """
        Check if Kyber secret key exists in HSM.
        
        Returns:
            True if key exists, False otherwise
        """
        try:
            self.load_kyber_secret_key()
            return True
        except ValueError:
            return False
    
    def close(self):
        """
        Close KeyStore (doesn't close singleton HSM session).
        """
        pass
