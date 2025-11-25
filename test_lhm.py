"""
Тестовий скрипт для перевірки LibreHardwareMonitor
Запустити ПЕРЕД основною програмою
"""
import sys
import os

# Додати поточну папку до path
sys.path.insert(0, os.path.dirname(__file__))

from logger import setup_logger
import logging

logger = setup_logger()

def test_lhm():
    """Тест інтеграції LHM"""
    logger.info("=== Testing LibreHardwareMonitor Integration ===")

    # Тест 1: Імпорт плагіну
    try:
        logger.info("Test 1: Importing LHM plugin...")
        from plugins.lhm_sensor import LhmSensor, HAS_LHM

        if not HAS_LHM:
            logger.error("FAIL: LibreHardwareMonitor not available")
            logger.error("Check:")
            logger.error("  1. pip install pythonnet")
            logger.error("  2. LibreHardwareMonitorLib.dll in plugins/lhm_sensor/")
            return False

        logger.info("PASS: LHM plugin imported successfully")
    except Exception as e:
        logger.error(f"FAIL: Cannot import LHM plugin: {e}", exc_info=True)
        return False

    # Тест 2: Ініціалізація сенсора
    try:
        logger.info("Test 2: Initializing LHM sensor...")
        sensor = LhmSensor()
        logger.info("PASS: LHM sensor initialized")
    except Exception as e:
        logger.error(f"FAIL: Cannot initialize sensor: {e}", exc_info=True)
        return False

    # Тест 3: Читання температури
    try:
        logger.info("Test 3: Reading CPU temperature...")
        temp = sensor.get_temperature()

        if temp is None or temp < 10 or temp > 100:
            logger.warning(f"WARNING: Suspicious temperature value: {temp}°C")
        else:
            logger.info(f"PASS: CPU Temperature: {temp}°C")
    except Exception as e:
        logger.error(f"FAIL: Cannot read temperature: {e}", exc_info=True)
        return False

    # Тест 4: Читання RPM
    try:
        logger.info("Test 4: Reading fan RPM...")
        rpm = sensor.get_fan_rpm(0)
        logger.info(f"PASS: Fan 0 RPM: {rpm}")

        rpm = sensor.get_fan_rpm(1)
        logger.info(f"INFO: Fan 1 RPM: {rpm}")
    except Exception as e:
        logger.error(f"FAIL: Cannot read RPM: {e}", exc_info=True)
        return False

    # Тест 5: Закриття
    try:
        logger.info("Test 5: Shutting down sensor...")
        sensor.shutdown()
        logger.info("PASS: Sensor shut down successfully")
    except Exception as e:
        logger.error(f"FAIL: Error during shutdown: {e}", exc_info=True)
        return False

    logger.info("=== ALL TESTS PASSED ===")
    return True

if __name__ == "__main__":
    success = test_lhm()

    if not success:
        logger.error("\nFailed! See errors above.")
        input("Press Enter to exit...")
        sys.exit(1)
    else:
        logger.info("\nSuccess! You can now run the main application.")
        input("Press Enter to exit...")
