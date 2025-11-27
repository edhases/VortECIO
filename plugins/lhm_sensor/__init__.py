"""
LibreHardwareMonitor Sensor Plugin
Забезпечує читання температури CPU, GPU, RPM вентиляторів
"""
import logging
import os
import sys

# Redundant unblocking for safety
if sys.platform == 'win32':
    try:
        from utils import unblock_file
        plugin_dir = os.path.dirname(__file__)
        unblock_file(os.path.join(plugin_dir, 'LibreHardwareMonitorLib.dll'))
        unblock_file(os.path.join(plugin_dir, 'HidSharp.dll'))
    except Exception as e:
        logging.getLogger('FanControl.LHM').error(f"Pre-emptive unblock failed: {e}")


logger = logging.getLogger('FanControl.LHM')

# Спроба завантажити LibreHardwareMonitor
HAS_LHM = False
try:
    import clr

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

        logger.info("Initializing LibreHardwareMonitor Computer")

        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsMotherboardEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsMemoryEnabled = False  # Не потрібна RAM
        self.computer.IsStorageEnabled = False  # Не потрібні диски
        self.computer.IsNetworkEnabled = False  # Не потрібна мережа

        self._logged_cpu_source = False

        try:
            self.computer.Open()
            logger.info("LHM Computer opened successfully")
            self._log_available_hardware()
        except Exception as e:
            logger.error(f"Failed to open LHM Computer: {e}")
            raise

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
        Universal temperature detection for all CPU types.
        Priority order:
        1. CPU Package (Intel standard)
        2. Tctl/Tdie (AMD Ryzen standard) - NOT a fallback!
        3. Core Average (generic fallback)
        4. Core #0/Core 1 (old CPUs)
        5. ANY temperature sensor (desperate fallback)
        """
        cpu_temp = None
        gpu_temp = None
        cpu_sensor_name = None

        # Find CPU hardware
        for hardware in self.computer.Hardware:
            if hardware.HardwareType == HardwareType.Cpu:
                hardware.Update()

                # Collect all temperature sensors
                temp_sensors = []
                for sensor in hardware.Sensors:
                    if sensor.SensorType == SensorType.Temperature and sensor.Value is not None:
                        temp_sensors.append((sensor.Name, sensor.Value))

                # Priority 1: CPU Package (Intel standard)
                for name, value in temp_sensors:
                    if "package" in name.lower():
                        cpu_temp = value
                        cpu_sensor_name = name
                        break

                # Priority 2: Tctl/Tdie (AMD Ryzen standard - NOT FALLBACK!)
                if cpu_temp is None:
                    for name, value in temp_sensors:
                        if "tctl" in name.lower() or "tdie" in name.lower():
                            cpu_temp = value
                            cpu_sensor_name = name
                            break

                # Priority 3: Core Average (generic)
                if cpu_temp is None:
                    for name, value in temp_sensors:
                        if "average" in name.lower() and "core" in name.lower():
                            cpu_temp = value
                            cpu_sensor_name = name
                            break

                # Priority 4: Core #0 / Core 1 (old CPUs)
                if cpu_temp is None:
                    for name, value in temp_sensors:
                        if "core" in name.lower() and any(c.isdigit() for c in name):
                            cpu_temp = value
                            cpu_sensor_name = name
                            break

                # Priority 5: ANY temperature - use MAX for safety
                if cpu_temp is None and len(temp_sensors) > 0:
                    max_sensor = max(temp_sensors, key=lambda x: x[1])
                    cpu_temp = max_sensor[1]
                    cpu_sensor_name = f"Max of {len(temp_sensors)} sensors"
                    self.logger.warning(f"Using generic fallback: {cpu_sensor_name}")

                # Log sensor source ONCE at startup (not every second!)
                if cpu_temp is not None and not self._logged_cpu_source:
                    self.logger.info(f"✓ CPU temperature source: {cpu_sensor_name} = {cpu_temp:.1f}°C")
                    self._logged_cpu_source = True

                break  # Found CPU

        # Find GPU hardware (same universal logic)
        for hardware in self.computer.Hardware:
            if hardware.HardwareType in (HardwareType.GpuAmd, HardwareType.GpuNvidia, HardwareType.GpuIntel):
                hardware.Update()

                temp_sensors = []
                for sensor in hardware.Sensors:
                    if sensor.SensorType == SensorType.Temperature and sensor.Value is not None:
                        temp_sensors.append((sensor.Name, sensor.Value))

                # Priority 1: GPU Core / GPU Temperature
                for name, value in temp_sensors:
                    if "core" in name.lower() or "gpu" in name.lower():
                        gpu_temp = value
                        break

                # Priority 2: ANY temperature
                if gpu_temp is None and len(temp_sensors) > 0:
                    gpu_temp = temp_sensors[0][1]

                if gpu_temp is not None:
                    break

        # Error handling
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
