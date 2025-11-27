"""Generate SHA-256 hashes for DLL verification."""
import hashlib
import os

def get_hash(filepath):
    if not os.path.exists(filepath):
        return f"FILE NOT FOUND: {filepath}"
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

print("=== DLL Hash Generation ===")
print(f"'inpoutx64.dll': '{get_hash('inpoutx64.dll')}',")
print(f"'LibreHardwareMonitorLib.dll': '{get_hash('plugins/lhm_sensor/LibreHardwareMonitorLib.dll')}',")
print("\nCopy these to KNOWN_HASHES in main.py")
