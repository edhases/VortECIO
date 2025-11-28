"""
LibreHardwareMonitor Sensor Plugin
Забезпечує читання температури CPU, GPU, RPM вентиляторів
"""
import logging
import os

logger = logging.getLogger('FanControl.LHM')

# Спроба завантажити LibreHardwareMonitor
HAS_LHM = False
try:
    import clr
    import sys

    # Знайти DLL
    dll_path = os.path.join(os.path.dirname(__file__), 'LibreHardwareMonitorLib.dll')

    if not os.path.exists(dll_path):
        logger.error(f"LibreHardwareMonitorLib.dll not found at: {dll_path}")
        logger.error("Download from: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases")
    else:
        # Додати до .NET references
        clr.AddReference(dll_path)
        from LibreHardwareMonitor.Hardware import Computer, HardwareType, SensorType
        HAS_LHM = True
        logger.info("LibreHardwareMonitor loaded successfully")

except ImportError as e:
    logger.error(f"pythonnet not installed: {e}")
    logger.error("Install with: pip install pythonnet")
except Exception as e:
    logger.error(f"Failed to load LibreHardwareMonitor: {e}")


class LhmSensor:
    """
    Sensor що використовує LibreHardwareMonitor для читання:
    - Температури CPU (per-core та package)
    - Температури GPU
    - RPM вентиляторів
    - Напруги
    """

    def __init__(self):
        if not HAS_LHM:
            raise ImportError("LibreHardwareMonitor not available")

        self.logger = logging.getLogger('FanControl.LHM')
        self.logger.info("Initializing LibreHardwareMonitor Computer")

        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsMotherboardEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsMemoryEnabled = False
        self.computer.IsStorageEnabled = False
        self.computer.IsNetworkEnabled = False

        self._logged_cpu_source = False
        self._cpu_hardware = None
        self._gpu_hardware = None

        try:
            self.computer.Open()
            logger.info("LHM Computer opened successfully")
            self._scan_hardware()
            self._log_available_hardware()
        except Exception as e:
            logger.error(f"Failed to open LHM Computer: {e}")
            raise

    def _scan_hardware(self):
        """
        Scans hardware ONCE and caches references to CPU and GPU devices.
        This is a critical performance optimization.
        """
        logger.info("Scanning for CPU and GPU hardware...")
        for hardware in self.computer.Hardware:
            if hardware.HardwareType == HardwareType.Cpu:
                self._cpu_hardware = hardware
                logger.info(f"✓ CPU hardware found: {hardware.Name}")
            elif hardware.HardwareType in (HardwareType.GpuAmd, HardwareType.GpuNvidia, HardwareType.GpuIntel):
                self._gpu_hardware = hardware
                logger.info(f"✓ GPU hardware found: {hardware.Name}")

        if not self._cpu_hardware:
            logger.warning("No CPU hardware found by LHM.")
        if not self._gpu_hardware:
            logger.warning("No GPU hardware found by LHM.")

    def _log_available_hardware(self):
        """Логування доступного обладнання (для дебагу)"""
        logger.info("=== Available Hardware ===")
        for hardware in self.computer.Hardware:
            logger.info(f"  {hardware.HardwareType}: {hardware.Name}")
            hardware.Update()

            # Логування сенсорів
            for sensor in hardware.Sensors:
                if sensor.Value is not None:
                    logger.debug(f"    [{sensor.SensorType}] {sensor.Name}: {sensor.Value}")
        logger.info("=========================")

    def get_temperatures(self):
        """
        Universal temperature detection using cached hardware references.
        Priority order:
        1. CPU Package (Intel standard)
        2. Tctl/Tdie (AMD Ryzen standard)
        3. Core Average (generic fallback)
        4. Core #0/Core 1 (old CPUs)
        5. ANY temperature sensor (desperate fallback)
        """
        cpu_temp = None
        gpu_temp = None
        cpu_sensor_name = None

        # Find CPU temperature using cached reference
        if self._cpu_hardware:
            self._cpu_hardware.Update()
            temp_sensors = [(s.Name, s.Value) for s in self._cpu_hardware.Sensors if s.SensorType == SensorType.Temperature and s.Value is not None]

            # Priority 1: CPU Package
            for name, value in temp_sensors:
                if "package" in name.lower():
                    cpu_temp = value
                    cpu_sensor_name = name
                    break

            # Priority 2: Tctl/Tdie
            if cpu_temp is None:
                for name, value in temp_sensors:
                    if "tctl" in name.lower() or "tdie" in name.lower():
                        cpu_temp = value
                        cpu_sensor_name = name
                        break

            # Priority 3: Core Average
            if cpu_temp is None:
                for name, value in temp_sensors:
                    if "average" in name.lower() and "core" in name.lower():
                        cpu_temp = value
                        cpu_sensor_name = name
                        break

            # Priority 4: Core #0 / Core 1
            if cpu_temp is None:
                for name, value in temp_sensors:
                    if "core" in name.lower() and any(c.isdigit() for c in name):
                        cpu_temp = value
                        cpu_sensor_name = name
                        break

            # Priority 5: ANY temperature (MAX)
            if cpu_temp is None and temp_sensors:
                max_sensor = max(temp_sensors, key=lambda x: x[1])
                cpu_temp, cpu_sensor_name = max_sensor[1], f"Max of {len(temp_sensors)} sensors"
                self.logger.warning(f"Using generic fallback for CPU: {cpu_sensor_name}")

            if cpu_temp is not None and not self._logged_cpu_source:
                self.logger.info(f"✓ CPU temperature source: {cpu_sensor_name} = {cpu_temp:.1f}°C")
                self._logged_cpu_source = True

        # Find GPU temperature using cached reference
        if self._gpu_hardware:
            self._gpu_hardware.Update()
            temp_sensors = [(s.Name, s.Value) for s in self._gpu_hardware.Sensors if s.SensorType == SensorType.Temperature and s.Value is not None]

            # Priority 1: GPU Core / GPU Temperature
            for name, value in temp_sensors:
                if "core" in name.lower() or "gpu" in name.lower():
                    gpu_temp = value
                    break

            # Priority 2: ANY temperature
            if gpu_temp is None and temp_sensors:
                gpu_temp = temp_sensors[0][1]

        if cpu_temp is None:
            self.logger.error("❌ No CPU temperature sensors found in LHM!")

        return cpu_temp, gpu_temp

    def shutdown(self):
        """Закриття з'єднання з LHM"""
        logger.info("Shutting down LibreHardwareMonitor")
        try:
            if hasattr(self, 'computer'):
                self.computer.Close()
                logger.info("LHM Computer closed successfully")
        except Exception as e:
            logger.error(f"Error closing LHM: {e}")


def register(app_logic):
    """
    Функція реєстрації плагіну (викликається PluginManager)

    Args:
        app_logic: екземпляр AppLogic
    Returns:
        LhmSensor instance або None якщо помилка
    """
    if not HAS_LHM:
        logger.error("Cannot register LHM sensor - library not available")
        logger.error("Install: pip install pythonnet")
        logger.error("Download DLL: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases")
        return None

    try:
        logger.info("Registering LibreHardwareMonitor sensor plugin")
        sensor = LhmSensor()
        app_logic.register_sensor(sensor)
        logger.info("LHM sensor plugin registered successfully")
        return sensor

    except Exception as e:
        logger.error(f"Failed to initialize LHM sensor: {e}", exc_info=True)
        return None
