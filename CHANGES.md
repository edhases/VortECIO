# Critical Bug Fixes - 2025-11-27

## Tier 1: Critical Blockers

### Priority #1: CPU Busy-Wait (hardware.py)
- Added 100μs sleep in _wait_ibf() and _wait_obf()
- Reduces CPU usage from ~100% to <1% during EC waits

### Priority #2: XML Validation (main.py)
- Added range checks for all NBFC config values
- Prevents hardware damage from malicious configs
- Preserves support for inverted fan speed ranges

### Priority #3: Panic Mode Redesign (fan_controller.py, main.py, ui/settings_window.py)
- Replaced permanent fan control disabling with a user-configurable action (ask, disable, continue, ignore).
- Added a settings UI to manage this behavior.

### Priority #4: Universal LHM Temperature Detection (plugins/lhm_sensor.py)
- Implemented a universal detection algorithm for CPU temperature that correctly identifies AMD and Intel sensors.
- Prevents log spam by reporting the detected sensor source only once.

## Tier 2: High Priority Fixes

### Priority #5: PyInstaller Compatibility (hardware.py)
- Implemented `sys.frozen` check to correctly locate DLLs when compiled to an EXE.

### Priority #6: Language Change UI Update (main.py)
- Fixed a bug where changing the language did not update the UI by ensuring the UI is recreated and the old settings window is closed.

### Priority #7: Theme Change Bug (main.py)
- Fixed a bug where changing the theme could corrupt the settings window by ensuring it is closed upon theme change.

### Priority #8: Enable LHM by Default (config.py, main.py)
- LHM is now the preferred temperature sensor by default if the plugin is available.

## Tier 3: Medium Priority Fixes

### Priority #9: DLL Hash Verification (PARTIALLY IMPLEMENTED)
- Added `verify_and_unblock()` function structure.
- Hash verification is DISABLED pending manual hash generation by the user.
- Added `generate_hashes.py` helper script for user.

### Priority #10: Hysteresis Fallback (fan_controller.py)
- Added fallback logic to handle hysteresis correctly after a manual fan speed override.

### Priority #11: Plugin Manager UI Style (ui/plugin_manager_window.py)
- This was not part of the active fixes and is deferred.
