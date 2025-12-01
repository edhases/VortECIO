"""
LibreHardwareMonitor Sensor Plugin
Optimized for caching hardware references to prevent UI lag.
"""
import logging
import os
from typing import Optional

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
        self.computer.IsMotherboardEnabled = True  # Enable for RPM reading
        self.computer.IsMemoryEnabled = False
        self.computer.IsStorageEnabled = False
        self.computer.IsNetworkEnabled = False
        self.computer.IsControllerEnabled = False

        self._cpu_hardware = None
        self._gpu_hardware = None
        self._motherboard_hardware = None # Add new field

        try:
            self.computer.Open()
            self._scan_hardware()
        except Exception as e:
            self.logger.error(f"Failed to open LHM: {e}")
            raise

    def _scan_hardware(self):
        """Cache hardware with priority for discrete GPU"""
        self.logger.info("Scanning hardware components...")

        discrete_gpu = None
        integrated_gpu = None

        for hardware in self.computer.Hardware:
            if hardware.HardwareType == HardwareType.Cpu:
                self._cpu_hardware = hardware
                self.logger.info(f"✓ Found CPU: {hardware.Name}")

            # DISCRETE GPU
            elif hardware.HardwareType in (HardwareType.GpuAmd, HardwareType.GpuNvidia):
                discrete_gpu = hardware
                self.logger.info(f"✓ Found discrete GPU: {hardware.Name}")

            # INTEGRATED GPU
            elif hardware.HardwareType == HardwareType.GpuIntel:
                integrated_gpu = hardware
                self.logger.info(f"✓ Found integrated GPU: {hardware.Name}")

            # MOTHERBOARD (for RPM)
            elif hardware.HardwareType == HardwareType.Motherboard:
                self._motherboard_hardware = hardware
                self.logger.info(f"✓ Found Motherboard: {hardware.Name}")

        # PRIORITY: discrete > integrated
        self._gpu_hardware = discrete_gpu or integrated_gpu

        if self._gpu_hardware:
            self.logger.info(f"→ Using GPU: {self._gpu_hardware.Name}")

    def get_temperatures(self):
        cpu_temp = None
        gpu_temp = None

        if self._cpu_hardware:
            try:
                self._cpu_hardware.Update()
                sensors = [s for s in self._cpu_hardware.Sensors
                          if s.SensorType == SensorType.Temperature and s.Value is not None]

                for s in sensors:
                    if "package" in s.Name.lower() or "tctl" in s.Name.lower():
                        cpu_temp = s.Value
                        break

                if cpu_temp is None and sensors:
                    cpu_temp = max(s.Value for s in sensors)
            except Exception as e:
                self.logger.warning(f"Failed to read CPU temperature: {e}")

        if self._gpu_hardware:
            try:
                self._gpu_hardware.Update()
                sensors = [s for s in self._gpu_hardware.Sensors
                          if s.SensorType == SensorType.Temperature and s.Value is not None]

                for s in sensors:
                    if "core" in s.Name.lower():
                        gpu_temp = s.Value
                        break

                if gpu_temp is None and sensors:
                    gpu_temp = sensors[0].Value
            except Exception as e:
                self.logger.warning(f"Failed to read GPU temperature: {e}")

        return cpu_temp, gpu_temp

    def get_fan_rpm(self, fan_index: int = 0) -> Optional[int]:
        """Read actual fan RPM from motherboard sensors."""
        if not self._motherboard_hardware:
            return None

        try:
            self._motherboard_hardware.Update()
            fans = [s for s in self._motherboard_hardware.Sensors
                    if s.SensorType == SensorType.Fan and s.Value is not None]

            if 0 <= fan_index < len(fans):
                return int(fans[fan_index].Value)
        except Exception as e:
            self.logger.warning(f"Failed to read fan #{fan_index} RPM: {e}")

        return None

    def shutdown(self):
        try:
            self.computer.Close()
        except: pass

def register(app_logic):
    if not HAS_LHM: return None
    try:
        sensor = LhmSensor()
        app_logic.register_sensor(sensor)
        return sensor
    except Exception as e:
        logger.error(f"Failed to initialize LHM sensor: {e}", exc_info=True)
        return None
