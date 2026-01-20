# hsm/soft_hsm_config.py

# SOFTHSM_LIB_PATH = r"C:\SoftHSM2\lib\softhsm2-x64.dll"



# TOKEN_LABEL = "IMAGE_ENC_TOKEN"
# USER_PIN = "1234"
# SLOT_INDEX = 0


# hsm/soft_hsm_config.py - UPDATE FOR WSL
# hsm/soft_hsm_config.py

import os
import platform

def is_wsl():
    """Check if running in WSL"""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

# Determine paths
if is_wsl() or platform.system() == "Linux":
    # WSL/Linux
    SOFTHSM_LIB_PATH = "/usr/lib/x86_64-linux-gnu/softhsm/libsofthsm2.so"
    
    # Set config file environment variable
    softhsm_conf = os.path.expanduser("~/.config/softhsm2/softhsm2.conf")
    if os.path.exists(softhsm_conf):
        os.environ['SOFTHSM2_CONF'] = softhsm_conf
else:
    # Windows
    SOFTHSM_LIB_PATH = r"C:\SoftHSM2\lib\softhsm2-x64.dll"

TOKEN_LABEL = "my_test_token"
USER_PIN = "1234"
SO_PIN = "1234"

print(f"[Config] Environment: {'WSL/Linux' if is_wsl() or platform.system() == 'Linux' else 'Windows'}")
print(f"[Config] SoftHSM library: {SOFTHSM_LIB_PATH}")
print(f"[Config] Library exists: {os.path.exists(SOFTHSM_LIB_PATH)}")
if 'SOFTHSM2_CONF' in os.environ:
    print(f"[Config] SoftHSM config: {os.environ['SOFTHSM2_CONF']}")
