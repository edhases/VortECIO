from typing import Dict, Any

def normalize_fan_speed(raw_value: int, fan_config: Dict[str, Any], min_val: int = None, max_val: int = None) -> int:
    # Use provided min/max if available, otherwise fall back to fan_config
    min_val = min_val if min_val is not None else fan_config['min_speed']
    max_val = max_val if max_val is not None else fan_config['max_speed']

    # Prevent division by zero if min and max are the same
    if min_val == max_val:
        return 0 if raw_value <= min_val else 100

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

from typing import Optional
import logging

logger = logging.getLogger(__name__)

def validate_temperature(temp: Optional[float], name: str) -> Optional[float]:
    """Check if a temperature is within a reasonable range."""
    if temp is None:
        return None

    if not (0 <= temp <= 120):  # Reasonable range for CPU/GPU
        logger.warning(f"Invalid {name} temperature detected: {temp}°C. Ignoring value.")
        return None

    return temp
