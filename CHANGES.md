# Critical Bug Fixes - 2025-11-27

## Priority #1: CPU Busy-Wait (hardware.py)
- Added 100μs sleep in _wait_ibf() and _wait_obf()
- Reduces CPU usage from ~100% to <1% during EC waits

## Priority #2: XML Validation (main.py)
- Added range checks for all NBFC config values
- Prevents hardware damage from malicious configs

## Priority #3: PyInstaller Compatibility (hardware.py)
- Implemented `sys.frozen` check to correctly locate DLLs when compiled to an EXE.

## Priority #4: DLL Hash Verification (PARTIALLY IMPLEMENTED)
- Added verify_and_unblock() function structure
- Hash verification DISABLED pending hash generation
- User must manually generate hashes and update KNOWN_HASHES dict before release

## Priority #5: Hysteresis Fallback (fan_controller.py)
- Added fallback logic to handle hysteresis correctly after a manual fan speed override.
