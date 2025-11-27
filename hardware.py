import ctypes
import time
import os
import sys
import threading
from typing import Optional
from logger import get_logger
from advanced_logging import get_detailed_logger

class EcDriver:
    def __init__(self, dll_name: str = 'inpoutx64.dll', ec_data_port: int = 0x62, ec_command_port: int = 0x66) -> None:
        self.logger = get_logger(__name__)
        # Determine base path (works for both script and compiled EXE)
        if getattr(sys, 'frozen', False):
            # Running as compiled EXE (PyInstaller)
            base_path = sys._MEIPASS  # PyInstaller temp folder
        else:
            # Running as Python script
            base_path = os.path.dirname(os.path.abspath(__file__))

        self.dll_path = os.path.join(base_path, dll_name)

        # Verify DLL exists before loading
        if not os.path.exists(self.dll_path):
            raise FileNotFoundError(f"Driver DLL not found: {self.dll_path}")

        self.logger.info(f"Loading driver from: {self.dll_path}")
        self.inpout: Optional[ctypes.WinDLL] = None
        self.is_initialized: bool = False
        self.lock: threading.Lock = threading.Lock()

        self.EC_DATA: int = ec_data_port
        self.EC_SC: int = ec_command_port
        self.EC_CMD_READ: int = 0x80
        self.EC_CMD_WRITE: int = 0x81
        self.EC_IBF: int = 0x02
        self.EC_OBF: int = 0x01
        self._load_driver()

    def _load_driver(self) -> None:
        if not os.path.exists(self.dll_path):
            self.is_initialized = False
            return
        try:
            self.inpout = ctypes.windll.LoadLibrary(self.dll_path)
            self.inpout.IsInpOutDriverOpen.restype = ctypes.c_int
            self.inpout.Out32.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
            self.inpout.Inp32.argtypes = [ctypes.c_ushort]
            self.inpout.Inp32.restype = ctypes.c_ushort
            self.is_initialized = bool(self.inpout.IsInpOutDriverOpen())
        except (OSError, AttributeError):
            self.is_initialized = False

    def _wait_ibf(self) -> bool:
        if not self.inpout: return False
        timeout = 0.1
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            if not (self.inpout.Inp32(self.EC_SC) & self.EC_IBF):
                return True
            time.sleep(0.0001)  # 100 microseconds - imperceptible latency, massive CPU savings
        return False

    def _wait_obf(self) -> bool:
        if not self.inpout: return False
        timeout = 0.1
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            if self.inpout.Inp32(self.EC_SC) & self.EC_OBF:
                return True
            time.sleep(0.0001)  # 100 microseconds - imperceptible latency, massive CPU savings
        return False

    def read_register(self, reg: int) -> Optional[int]:
        if not self.is_initialized or not self.inpout:
            return None
        with self.lock:
            if not self._wait_ibf(): return None
            self.inpout.Out32(self.EC_SC, self.EC_CMD_READ)
            if not self._wait_ibf(): return None
            self.inpout.Out32(self.EC_DATA, reg)
            if not self._wait_obf(): return None
            result = self.inpout.Inp32(self.EC_DATA)
            detailed_logger = get_detailed_logger()
            if detailed_logger:
                detailed_logger.log_ec_operation('read', reg, result, success=True)
            return result

    def write_register(self, reg: int, val: int) -> bool:
        if not self.is_initialized or not self.inpout:
            return False
        with self.lock:
            success = False
            if not self._wait_ibf(): return False
            self.inpout.Out32(self.EC_SC, self.EC_CMD_WRITE)
            if not self._wait_ibf(): return False
            self.inpout.Out32(self.EC_DATA, reg)
            if not self._wait_ibf(): return False
            self.inpout.Out32(self.EC_DATA, val)
            success = True
            detailed_logger = get_detailed_logger()
            if detailed_logger:
                detailed_logger.log_ec_operation('write', reg, val, success=success)
            return success
