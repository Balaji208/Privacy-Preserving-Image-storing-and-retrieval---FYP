# hsm/hsm_manager.py

from pkcs11 import lib, Attribute, ObjectClass, KeyType
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
        self.session = self.token.open(user_pin=USER_PIN)

    def store_secret(self, label: str, secret: bytes):
        self.session.create_object({
            Attribute.CLASS: ObjectClass.SECRET_KEY,
            Attribute.KEY_TYPE: KeyType.GENERIC_SECRET,
            Attribute.LABEL: label,
            Attribute.VALUE: secret,
            Attribute.SENSITIVE: True,
            Attribute.EXTRACTABLE: False,
        })

    def store_secret_test(self, label: str, secret: bytes):
        print(f"[HSM] Storing secret with label={label}, len={len(secret)}")
        obj = self.session.create_object({
            Attribute.CLASS: ObjectClass.SECRET_KEY,
            Attribute.KEY_TYPE: KeyType.GENERIC_SECRET,
            Attribute.LABEL: label,
            Attribute.VALUE: secret,
            Attribute.SENSITIVE: False,
            Attribute.EXTRACTABLE: True,
        })
        print(f"[HSM] Created object: {obj}")

    def retrieve_secret(self, label: str) -> bytes:
        for obj in self.session.get_objects({Attribute.LABEL: label}):
            return obj[Attribute.VALUE]
        raise ValueError(f"Secret with label {label} not found")

    def close(self):
        self.session.close()

    def debug_list_objects(self):
        print("=== HSM objects ===")
        for obj in self.session.get_objects():
            try:
                # Attribute access is mapping-style, not obj.get(...)
                raw_label = obj[Attribute.LABEL]
            except KeyError:
                raw_label = b""

            try:
                label_str = raw_label.decode(errors="ignore")
            except Exception:
                label_str = str(raw_label)

            print("Object:", obj, "LABEL:", label_str)
        print("=== End HSM objects ===")



def get_hsm_manager() -> HSMManager:
    global _hsm_manager_singleton
    if _hsm_manager_singleton is None:
        _hsm_manager_singleton = HSMManager()
    return _hsm_manager_singleton
