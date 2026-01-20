# hsm/hsm_manager.py 

from pkcs11 import lib, Attribute, ObjectClass, KeyType
from pkcs11.exceptions import UserAlreadyLoggedIn
from hsm.soft_hsm_config import (
    SOFTHSM_LIB_PATH,
    TOKEN_LABEL,
    USER_PIN,
)


_hsm_manager_singleton = None


class HSMManager:
    """
    SoftHSM Manager
    - Loads PKCS#11 library
    - Opens secure session
    - Handles key storage & retrieval
    """
    
    def __init__(self):
        self.lib = lib(SOFTHSM_LIB_PATH)
        self.token = self.lib.get_token(token_label=TOKEN_LABEL)
        
        # Open session with authentication
        try:
            self.session = self.token.open(rw=True, user_pin=USER_PIN)
            print("[HSM] Session opened and authenticated")
        except UserAlreadyLoggedIn:
            print("[HSM] User already logged in, opening session without PIN")
            self.session = self.token.open(rw=True)
        except Exception as e:
            print(f"[HSM] Warning: {e}")
            self.session = self.token.open(rw=True)
    
    def store_secret(self, label: str, secret: bytes):
        """Store secret key (non-extractable, sensitive)"""
        obj = self.session.create_object({
            Attribute.CLASS: ObjectClass.SECRET_KEY,
            Attribute.KEY_TYPE: KeyType.GENERIC_SECRET,
            Attribute.LABEL: label,
            Attribute.VALUE: secret,
            Attribute.SENSITIVE: True,
            Attribute.EXTRACTABLE: False,
            Attribute.TOKEN: True,
        })
        print(f"[HSM] Stored secret: {label}")
        return obj
    
    def store_secret_test(self, label: str, secret: bytes):
        """Store secret key (extractable for testing) - FIXED WITH EXTRACTABLE=True"""
        print(f"[HSM] Storing secret with label={label}, len={len(secret)}")
        
        obj = self.session.create_object({
            Attribute.CLASS: ObjectClass.SECRET_KEY,
            Attribute.KEY_TYPE: KeyType.GENERIC_SECRET,
            Attribute.LABEL: label,
            Attribute.VALUE: secret,
            Attribute.SENSITIVE: False,      # ← MUST BE FALSE TO READ VALUE
            Attribute.EXTRACTABLE: True,     # ← MUST BE TRUE TO READ VALUE
            Attribute.TOKEN: True,
        })
        
        print(f"[HSM] ✓ Created object: {obj}")
        return obj
    
    def retrieve_secret(self, label: str) -> bytes:
        """Retrieve secret key by label"""
        # Iterate through all objects and find matching label
        for obj in self.session.get_objects():
            try:
                obj_label = obj[Attribute.LABEL]
                
                # Normalize label for comparison
                if isinstance(obj_label, bytes):
                    obj_label_str = obj_label.decode('utf-8', errors='ignore').strip()
                elif obj_label:
                    obj_label_str = str(obj_label).strip()
                else:
                    continue
                
                # Match found
                if obj_label_str == label:
                    # Check if extractable
                    try:
                        is_extractable = obj[Attribute.EXTRACTABLE]
                        if not is_extractable:
                            raise ValueError(f"Secret '{label}' is not extractable (SENSITIVE key)")
                    except:
                        pass  # Assume extractable if attribute not present
                    
                    return obj[Attribute.VALUE]
                    
            except (KeyError, AttributeError):
                continue
        
        raise ValueError(f"Secret with label '{label}' not found in HSM")
    
    def delete_secret(self, label: str):
        """Delete secret key by label"""
        deleted = False
        
        for obj in self.session.get_objects():
            try:
                obj_label = obj[Attribute.LABEL]
                
                if isinstance(obj_label, bytes):
                    obj_label_str = obj_label.decode('utf-8', errors='ignore').strip()
                elif obj_label:
                    obj_label_str = str(obj_label).strip()
                else:
                    continue
                
                if obj_label_str == label:
                    obj.destroy()
                    deleted = True
                    print(f"[HSM] Deleted object with label: {label}")
                    break
                    
            except (KeyError, AttributeError):
                continue
        
        if not deleted:
            raise ValueError(f"Secret with label '{label}' not found")
    
    def list_all_keys(self):
        """List all keys in HSM with details"""
        objects = list(self.session.get_objects())
        
        print(f"\n{'='*70}")
        print(f"HSM KEY INVENTORY")
        print(f"{'='*70}")
        print(f"Total objects: {len(objects)}\n")
        
        if not objects:
            print("⚠️  No keys found in HSM\n")
            return []
        
        keys_info = []
        for idx, obj in enumerate(objects, 1):
            # Extract label
            try:
                raw_label = obj[Attribute.LABEL]
                if isinstance(raw_label, bytes):
                    label = raw_label.decode('utf-8', errors='ignore').strip()
                elif raw_label:
                    label = str(raw_label).strip()
                else:
                    label = "(no label)"
                
                if not label:
                    label = "(no label)"
            except:
                label = "(no label)"
            
            # Extract object class
            try:
                obj_class = obj[Attribute.CLASS]
                class_map = {
                    ObjectClass.SECRET_KEY: "SECRET_KEY",
                    ObjectClass.PUBLIC_KEY: "PUBLIC_KEY",
                    ObjectClass.PRIVATE_KEY: "PRIVATE_KEY",
                }
                class_str = class_map.get(obj_class, str(obj_class))
            except:
                class_str = "UNKNOWN"
            
            # Extract size and preview (only if extractable)
            try:
                # Check if extractable first
                is_extractable = obj[Attribute.EXTRACTABLE]
                
                if is_extractable:
                    value = obj[Attribute.VALUE]
                    size = len(value)
                    preview = value[:8].hex()
                else:
                    size = "(sensitive)"
                    preview = "(not extractable)"
            except:
                size = 0
                preview = "N/A"
            
            info = {
                'index': idx,
                'label': label,
                'class': class_str,
                'size': size,
                'preview': preview
            }
            keys_info.append(info)
            
            # Format size for display
            if isinstance(size, int):
                size_str = f"{size:>10,} bytes"
            else:
                size_str = f"{str(size):>17}"
            
            print(f"[{idx}] {label:<30} | {class_str:<15} | {size_str}")
            if preview not in ["(not extractable)", "N/A"]:
                print(f"     Preview: {preview}...")
        
        print(f"{'='*70}\n")
        return keys_info
    
    def close(self):
        """Close HSM session"""
        try:
            self.session.close()
            print("[HSM] Session closed")
        except:
            pass
    
    def key_exists(self, label: str) -> bool:
        """Check if a key with given label exists"""
        try:
            self.retrieve_secret(label)
            return True
        except ValueError:
            return False
    
    def clear_all_keys(self):
        """Clear all keys from HSM. WARNING: This deletes ALL keys!"""
        deleted_count = 0
        
        for obj in self.session.get_objects():
            try:
                label = obj[Attribute.LABEL]
                if isinstance(label, bytes):
                    label = label.decode('utf-8', errors='ignore')
            except:
                label = "(no label)"
            
            obj.destroy()
            deleted_count += 1
            print(f"[HSM] Deleted: {label}")
        
        return deleted_count


def get_hsm_manager() -> HSMManager:
    """Get singleton HSM Manager instance"""
    global _hsm_manager_singleton
    if _hsm_manager_singleton is None:
        _hsm_manager_singleton = HSMManager()
    return _hsm_manager_singleton
