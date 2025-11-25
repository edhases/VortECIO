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

        logger.info("Initializing LibreHardwareMonitor Computer")

        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsMotherboardEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsMemoryEnabled = False  # Не потрібна RAM
        self.computer.IsStorageEnabled = False  # Не потрібні диски
        self.computer.IsNetworkEnabled = False  # Не потрібна мережа

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

    def get_temperature(self):
        """
        Читання температури CPU (основний метод для NBFC)
        Повертає: float - температура в °C
        """
        try:
            for hardware in self.computer.Hardware:
                hardware.Update()

                if hardware.HardwareType == HardwareType.Cpu:
                    # Пріоритет: CPU Package або Core Average
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == SensorType.Temperature:
                            if sensor.Value is not None:
                                # Шукаємо Package або Total
                                if "Package" in sensor.Name or "CPU Package" in sensor.Name:
                                    temp = float(sensor.Value)
                                    logger.debug(f"CPU Temp (Package): {temp}°C")
                                    return temp
                                elif "Average" in sensor.Name or "Core Average" in sensor.Name:
                                    temp = float(sensor.Value)
                                    logger.debug(f"CPU Temp (Average): {temp}°C")
                                    return temp

                    # Fallback: перша доступна температура CPU
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == SensorType.Temperature and sensor.Value:
                            temp = float(sensor.Value)
                            logger.warning(f"Using fallback CPU temp: {temp}°C from {sensor.Name}")
                            return temp

            # Якщо нічого не знайдено
            logger.error("No CPU temperature sensor found!")
            return 45.0  # Safe default

        except Exception as e:
            logger.error(f"Error reading temperature: {e}", exc_info=True)
            return 45.0

    def get_fan_rpm(self, fan_index=0):
        """
        Читання RPM вентилятора (замість EC ReadRegister)

        Args:
            fan_index: індекс вентилятора (0, 1, 2...)
        Returns:
            int - RPM або 0 якщо недоступно
        """
        try:
            for hardware in self.computer.Hardware:
                hardware.Update()

                if hardware.HardwareType == HardwareType.Motherboard:
                    # Зібрати всі fan sensors
                    fan_sensors = [s for s in hardware.Sensors
                                  if s.SensorType == SensorType.Fan]

                    if fan_index < len(fan_sensors):
                        sensor = fan_sensors[fan_index]
                        rpm = int(sensor.Value) if sensor.Value else 0
                        logger.debug(f"Fan {fan_index} ({sensor.Name}): {rpm} RPM")
                        return rpm
                    else:
                        logger.warning(f"Fan index {fan_index} not available (total: {len(fan_sensors)})")
                        return 0

            logger.warning("No motherboard/fan sensors found")
            return 0

        except Exception as e:
            logger.error(f"Error reading fan RPM: {e}", exc_info=True)
            return 0

    def get_gpu_temperature(self):
        """Читання температури GPU (додатково)"""
        try:
            for hardware in self.computer.Hardware:
                hardware.Update()

                if hardware.HardwareType == HardwareType.GpuNvidia or \
                   hardware.HardwareType == HardwareType.GpuAmd or \
                   hardware.HardwareType == HardwareType.GpuIntel:

                    for sensor in hardware.Sensors:
                        if sensor.SensorType == SensorType.Temperature and sensor.Value:
                            temp = float(sensor.Value)
                            logger.debug(f"GPU Temp: {temp}°C")
                            return temp

            return None
        except Exception as e:
            logger.error(f"Error reading GPU temperature: {e}")
            return None

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
