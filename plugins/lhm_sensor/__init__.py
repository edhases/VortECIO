"""
LibreHardwareMonitor Sensor Plugin
Optimized for caching hardware references to prevent UI lag.
"""
import logging
import os

logger = logging.getLogger('FanControl.LHM')

HAS_LHM = False
try:
    import clr
    import sys
    dll_path = os.path.join(os.path.dirname(__file__), 'LibreHardwareMonitorLib.dll')
    if not os.path.exists(dll_path):
        logger.error(f"LibreHardwareMonitorLib.dll not found at: {dll_path}")
    else:
        clr.AddReference(dll_path)
        from LibreHardwareMonitor.Hardware import Computer, HardwareType, SensorType
        HAS_LHM = True
        logger.info("LibreHardwareMonitor loaded successfully")
except Exception as e:
    logger.error(f"Failed to load LibreHardwareMonitor: {e}")

class LhmSensor:
    def __init__(self):
        if not HAS_LHM:
            raise ImportError("LibreHardwareMonitor not available")

        self.logger = logging.getLogger('FanControl.LHM')
        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsMotherboardEnabled = False
        self.computer.IsMemoryEnabled = False
        self.computer.IsStorageEnabled = False
        self.computer.IsNetworkEnabled = False
        self.computer.IsControllerEnabled = False

        self._cpu_hardware = None
        self._gpu_hardware = None

        try:
            self.computer.Open()
            self._scan_hardware()
        except Exception as e:
            self.logger.error(f"Failed to open LHM: {e}")
            raise

    def _scan_hardware(self):
        """Cache hardware references once at startup to avoid bus scanning lag."""
        self.logger.info("Scanning hardware components...")
        for hardware in self.computer.Hardware:
            if hardware.HardwareType == HardwareType.Cpu:
                self._cpu_hardware = hardware
                self.logger.info(f"✓ Found CPU: {hardware.Name}")
            elif hardware.HardwareType in (HardwareType.GpuAmd, HardwareType.GpuNvidia, HardwareType.GpuIntel):
                # Prefer discrete GPU or take the first one found if we haven't found one yet
                # Note: If you have both iGPU and dGPU, this logic grabs the first one.
                # LHM usually lists dGPU first or we can refine this if needed.
                if self._gpu_hardware is None or "intel" in self._gpu_hardware.Name.lower():
                    self._gpu_hardware = hardware
                    self.logger.info(f"✓ Found GPU: {hardware.Name}")

    def get_temperatures(self):
        cpu_temp = None
        gpu_temp = None

        # --- Read CPU ---
        if self._cpu_hardware:
            try:
                self._cpu_hardware.Update()
                sensors = [s for s in self._cpu_hardware.Sensors if s.SensorType == SensorType.Temperature and s.Value is not None]
                # Priority: Package -> Tctl/Tdie -> Core Max
                for s in sensors:
                    if "package" in s.Name.lower() or "tctl" in s.Name.lower():
                        cpu_temp = s.Value
                        break
                if cpu_temp is None and sensors:
                    cpu_temp = max(s.Value for s in sensors)
            except Exception:
                pass

        # --- Read GPU ---
        if self._gpu_hardware:
            try:
                self._gpu_hardware.Update()
                sensors = [s for s in self._gpu_hardware.Sensors if s.SensorType == SensorType.Temperature and s.Value is not None]
                # Priority: Hot Spot -> Core
                for s in sensors:
                    if "core" in s.Name.lower():
                        gpu_temp = s.Value
                        break
                if gpu_temp is None and sensors:
                    gpu_temp = sensors[0].Value
            except Exception:
                pass

        return cpu_temp, gpu_temp

    def shutdown(self):
        try:
            self.computer.Close()
        except: pass

def register(app_logic):
    if not HAS_LHM: return None
    return LhmSensor()
