"""
HSM Key Manager for LSH
=======================
Integrates with SoftHSM for secure HMAC key storage.
"""

import logging
from typing import Optional, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# Import HSM modules
try:
    from hsm.hsm_manager import get_hsm_manager
    HSM_AVAILABLE = True
except ImportError:
    HSM_AVAILABLE = False
    logger.warning("HSM modules not available. SoftHSM integration disabled.")


class HSMKeyManager:
    """
    Manages HMAC keys using SoftHSM.
    
    Key Labels:
        - LSH_HMAC_MASTER_KEY: Main HMAC key for tokenization
        - LSH_HMAC_BACKUP_KEY: Optional backup key
    """
    
    # Standard key labels
    MASTER_KEY_LABEL = "LSH_HMAC_MASTER_KEY"
    BACKUP_KEY_LABEL = "LSH_HMAC_BACKUP_KEY"
    
    def __init__(self, key_label: str = MASTER_KEY_LABEL):
        """
        Initialize HSM key manager.
        
        Args:
            key_label: Label for the key in HSM
        """
        if not HSM_AVAILABLE:
            raise RuntimeError(
                "HSM modules not available. Install python-pkcs11 and configure SoftHSM."
            )
        
        self.hsm = get_hsm_manager()
        self.key_label = key_label
        self._cache = {}
        self._lock = Lock()
        
        logger.info(f"Initialized HSM key manager with label: {key_label}")
    
    def store_hmac_key(
        self,
        key: bytes,
        overwrite: bool = False
    ) -> bool:
        """
        Store HMAC key in HSM.
        
        Args:
            key: 32-byte HMAC key
            overwrite: If True, delete existing key first
            
        Returns:
            True if stored successfully
        """
        if len(key) != 32:
            raise ValueError(f"HMAC key must be 32 bytes, got {len(key)}")
        
        try:
            # Check if key already exists
            if not overwrite:
                if self.key_exists():
                    logger.warning(
                        f"Key with label {self.key_label} already exists. "
                        f"Use overwrite=True to replace."
                    )
                    return False
            else:
                # Delete existing key
                self.delete_hmac_key()
            
            # Store new key with proper label encoding
            print(f"[HSMKeyManager] Storing key with label: {self.key_label}")
            self.hsm.store_secret_test(self.key_label, key)
            
            # Verify it was stored correctly
            if self.key_exists():
                logger.info(f"✓ Stored and verified HMAC key in HSM: {self.key_label}")
                return True
            else:
                logger.error(f"✗ Failed to verify stored key: {self.key_label}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to store HMAC key: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def retrieve_hmac_key(self) -> bytes:
        """
        Retrieve HMAC key from HSM.
        
        Returns:
            32-byte HMAC key
            
        Raises:
            ValueError: If key not found
        """
        try:
            # Try to retrieve with exact label
            try:
                key = self.hsm.retrieve_secret(self.key_label)
                
                if len(key) != 32:
                    logger.error(
                        f"Retrieved key has invalid length: {len(key)} (expected 32)"
                    )
                    raise ValueError(f"Invalid key length: {len(key)}")
                
                logger.debug(f"Retrieved HMAC key from HSM: {self.key_label}")
                return key
                
            except ValueError as first_error:
                # Label might have been stored differently, try to find it
                logger.warning(f"Direct retrieval failed, searching for key...")
                
                from pkcs11 import Attribute
                
                # Search for any key with similar label
                for obj in self.hsm.session.get_objects():
                    try:
                        raw_label = obj[Attribute.LABEL]
                        
                        # Handle different label encodings
                        if isinstance(raw_label, bytes):
                            label_str = raw_label.decode('utf-8', errors='ignore').strip()
                        else:
                            label_str = str(raw_label).strip()
                        
                        # Check if this is our key
                        if label_str == self.key_label or label_str == self.key_label.strip():
                            key = obj[Attribute.VALUE]
                            
                            if len(key) == 32:
                                logger.info(f"Found key with label: '{label_str}'")
                                return key
                    except Exception as e:
                        continue
                
                # If still not found, raise original error
                raise first_error
                
        except ValueError as e:
            logger.error(f"Key not found in HSM: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve HMAC key: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def delete_hmac_key(self) -> bool:
        """
        Delete HMAC key from HSM.
        
        Returns:
            True if deleted successfully
        """
        try:
            from pkcs11 import Attribute
            
            deleted = False
            
            # Find and delete all objects with this label
            for obj in self.hsm.session.get_objects():
                try:
                    raw_label = obj[Attribute.LABEL]
                    
                    if isinstance(raw_label, bytes):
                        label_str = raw_label.decode('utf-8', errors='ignore').strip()
                    else:
                        label_str = str(raw_label).strip()
                    
                    if label_str == self.key_label or label_str == self.key_label.strip():
                        obj.destroy()
                        logger.info(f"Deleted key from HSM: {label_str}")
                        deleted = True
                except Exception:
                    continue
            
            if not deleted:
                logger.warning(f"No key found to delete: {self.key_label}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete key: {e}")
            return False
    
    def key_exists(self) -> bool:
        """
        Check if HMAC key exists in HSM.
        
        Returns:
            True if key exists
        """
        try:
            from pkcs11 import Attribute
            
            # Search for key with matching label
            for obj in self.hsm.session.get_objects():
                try:
                    raw_label = obj[Attribute.LABEL]
                    
                    if isinstance(raw_label, bytes):
                        label_str = raw_label.decode('utf-8', errors='ignore').strip()
                    else:
                        label_str = str(raw_label).strip()
                    
                    if label_str == self.key_label or label_str == self.key_label.strip():
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking key existence: {e}")
            return False
    
    def list_all_keys(self) -> list:
        """
        List all LSH keys in HSM.
        
        Returns:
            List of key labels
        """
        try:
            from pkcs11 import Attribute
            
            keys = []
            for obj in self.hsm.session.get_objects():
                try:
                    raw_label = obj[Attribute.LABEL]
                    
                    if isinstance(raw_label, bytes):
                        label_str = raw_label.decode('utf-8', errors='ignore').strip()
                    else:
                        label_str = str(raw_label).strip()
                    
                    if label_str.startswith('LSH_'):
                        keys.append(label_str)
                except Exception:
                    continue
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []


def initialize_hmac_key_in_hsm(overwrite: bool = False) -> bytes:
    """
    Initialize HMAC key in HSM if not exists.
    
    Args:
        overwrite: Force generate new key
        
    Returns:
        HMAC key (32 bytes)
    """
    manager = HSMKeyManager()
    
    # Check if key exists
    if not overwrite and manager.key_exists():
        logger.info("HMAC key already exists in HSM, retrieving...")
        return manager.retrieve_hmac_key()
    
    # Generate new key
    from .security import SecurityUtils
    new_key = SecurityUtils.generate_hmac_key()
    
    # Store in HSM
    success = manager.store_hmac_key(new_key, overwrite=overwrite)
    
    if not success:
        raise RuntimeError("Failed to store HMAC key in HSM")
    
    logger.info("Generated and stored new HMAC key in HSM")
    return new_key


def load_hmac_key_from_hsm(key_label: str = HSMKeyManager.MASTER_KEY_LABEL) -> bytes:
    """
    Load HMAC key from HSM.
    
    Args:
        key_label: Label of key to load
        
    Returns:
        32-byte HMAC key
    """
    manager = HSMKeyManager(key_label)
    return manager.retrieve_hmac_key()
