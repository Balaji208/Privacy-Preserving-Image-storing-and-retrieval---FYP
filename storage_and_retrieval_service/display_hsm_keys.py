# display_keys.py

from hsm.hsm_manager import get_hsm_manager

hsm = get_hsm_manager()

# Summary view
hsm.list_all_keys()
