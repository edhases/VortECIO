from typing import Dict, Any
import sys
import os
import logging
import hashlib
from logger import get_logger

# TODO: Generate hashes using generate_hashes.py script
KNOWN_HASHES = {
    'inpoutx64.dll': None,  # User must fill this
    'LibreHardwareMonitorLib.dll': None,
}

def unblock_file(filepath: str) -> None:
    if sys.platform != 'win32':
        return
    ads_path = filepath + ":Zone.Identifier"
    try:
        if os.path.exists(ads_path):
            os.remove(ads_path)
            logging.info(f"Unblocked {os.path.basename(filepath)}")
    except OSError as e:
        logging.warning(f"Failed to unblock {os.path.basename(filepath)}: {e}")

def verify_and_unblock(filepath: str) -> bool:
    """
    Verify DLL integrity and remove MOTW if valid.
    NOTE: Hash verification disabled pending manual hash generation.
    """
    filename = os.path.basename(filepath)
    logger = get_logger(__name__)

    if filename in KNOWN_HASHES and KNOWN_HASHES[filename] is not None:
        # Hash verification enabled
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        if file_hash != KNOWN_HASHES[filename]:
            logger.error(f"❌ Hash mismatch for {filename}! Possible tampering.")
            return False
    else:
        # Hash not set - log warning but proceed
        logger.warning(f"⚠️ Hash verification not configured for {filename}")

    # Unblock file
    unblock_file(filepath)
    return True

def normalize_fan_speed(raw_value: int, fan_config: Dict[str, Any]) -> int:
    min_val = fan_config['min_speed']
    max_val = fan_config['max_speed']
    if fan_config.get('is_inverted', False):
        if raw_value >= min_val: return 0
        if raw_value <= max_val: return 100
        percent = 100 - int(((raw_value - max_val) / (min_val - max_val)) * 100)
    else:
        if raw_value <= min_val: return 0
        if raw_value >= max_val: return 100
        percent = int(((raw_value - min_val) / (max_val - min_val)) * 100)
    return max(0, min(100, percent))


def denormalize_fan_speed(percent: int, fan_config: Dict[str, Any]) -> int:
    min_val = fan_config['min_speed']
    max_val = fan_config['max_speed']
    if fan_config.get('is_inverted', False):
        raw = min_val - int(((min_val - max_val) * percent) / 100)
    else:
        raw = min_val + int(((max_val - min_val) * percent) / 100)
    lower_bound = min(min_val, max_val)
    upper_bound = max(min_val, max_val)
    return max(lower_bound, min(upper_bound, raw))
