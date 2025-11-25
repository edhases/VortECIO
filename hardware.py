import ctypes
import time
import os
import threading
from logger import get_logger

logger = get_logger('Hardware')

# EC Constants
EC_SC = 0x66
EC_DATA = 0x62
EC_CMD_READ = 0x80
EC_CMD_WRITE = 0x81
EC_IBF = 0x02
EC_OBF = 0x01

class EcDriver:
    """
    EC Driver використовуючи InpOutx64.dll
    ТІЛЬКИ для ЗАПИСУ в регістри (fan control)
    Читання температури через LibreHardwareMonitor
    """

    def __init__(self, dll_name='inpoutx64.dll'):
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.dll_path = os.path.join(base_path, dll_name)
        self.inpout = None
        self.lock = threading.Lock()
        self.is_initialized = False
        self._load_driver()

    def _load_driver(self):
        """Завантаження InpOutx64 драйвера"""
        if not os.path.exists(self.dll_path):
            logger.error(f"InpOutx64.dll not found at: {self.dll_path}")
            return False

        try:
            logger.info(f"Loading InpOutx64.dll from: {self.dll_path}")
            self.inpout = ctypes.windll.LoadLibrary(self.dll_path)
            self.inpout.IsInpOutDriverOpen.restype = ctypes.c_int
            self.inpout.Out32.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
            self.inpout.Inp32.argtypes = [ctypes.c_ushort]
            self.inpout.Inp32.restype = ctypes.c_ushort

            self.is_initialized = bool(self.inpout.IsInpOutDriverOpen())

            if self.is_initialized:
                logger.info("InpOutx64 driver opened successfully")
            else:
                logger.error("InpOutx64 driver failed to open (IsInpOutDriverOpen returned False)")
                logger.error("Make sure application runs with Administrator privileges")

            return self.is_initialized

        except Exception as e:
            logger.error(f"Failed to load InpOutx64: {e}", exc_info=True)
            self.is_initialized = False
            return False

    def _wait_ibf(self, timeout=0.2):
        """Wait for Input Buffer Flag to clear"""
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            status = self.inpout.Inp32(EC_SC)
            if not (status & EC_IBF):
                return True
            time.sleep(0.001)
        logger.warning(f"IBF timeout after {timeout}s")
        return False

    def _wait_obf(self, timeout=0.2):
        """Wait for Output Buffer Flag to set"""
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            status = self.inpout.Inp32(EC_SC)
            if status & EC_OBF:
                return True
            time.sleep(0.001)
        logger.warning(f"OBF timeout after {timeout}s")
        return False

    def read_register(self, reg):
        """
        Читання EC регістра (з retry логікою)
        ВИКОРИСТОВУЄТЬСЯ ТІЛЬКИ ДЛЯ ЧИТАННЯ RPM (не температури!)
        """
        if not self.is_initialized:
            logger.debug(f"Cannot read register 0x{reg:02X} - driver not initialized")
            return None

        # 3 спроби з exponential backoff
        for attempt in range(3):
            with self.lock:
                try:
                    if not self._wait_ibf():
                        continue

                    self.inpout.Out32(EC_SC, EC_CMD_READ)

                    if not self._wait_ibf():
                        continue

                    self.inpout.Out32(EC_DATA, reg)

                    if not self._wait_obf():
                        continue

                    value = self.inpout.Inp32(EC_DATA)
                    logger.debug(f"Read EC register 0x{reg:02X} = 0x{value:02X} (attempt {attempt + 1})")
                    return value

                except Exception as e:
                    logger.error(f"Error reading register 0x{reg:02X}: {e}")
                    continue

            # Пауза між спробами (exponential backoff)
            if attempt < 2:
                sleep_time = 0.025 * (attempt + 1)  # 25ms, 50ms
                time.sleep(sleep_time)

        logger.warning(f"Failed to read register 0x{reg:02X} after 3 attempts")
        return None

    def write_register(self, reg, value):
        """
        Запис в EC регістр (для fan control)
        """
        if not self.is_initialized:
            logger.error(f"Cannot write register 0x{reg:02X} - driver not initialized")
            return False

        with self.lock:
            try:
                if not self._wait_ibf():
                    return False

                self.inpout.Out32(EC_SC, EC_CMD_WRITE)

                if not self._wait_ibf():
                    return False

                self.inpout.Out32(EC_DATA, reg)

                if not self._wait_ibf():
                    return False

                self.inpout.Out32(EC_DATA, value)

                logger.info(f"Wrote EC register 0x{reg:02X} = 0x{value:02X}")
                return True

            except Exception as e:
                logger.error(f"Error writing register 0x{reg:02X}: {e}", exc_info=True)
                return False
