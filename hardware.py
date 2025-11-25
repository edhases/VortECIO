import ctypes
import time
import os
import threading

EC_SC = 0x66
EC_DATA = 0x62
EC_CMD_READ = 0x80
EC_CMD_WRITE = 0x81
EC_IBF = 0x02
EC_OBF = 0x01

class EcDriver:
    def __init__(self, dll_name='inpoutx64.dll'):
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.dll_path = os.path.join(base_path, dll_name)
        self.inpout = None
        self.is_initialized = False
        self.lock = threading.Lock() # Thread safety lock
        self._load_driver()

    def _load_driver(self):
        if not os.path.exists(self.dll_path): return False
        try:
            self.inpout = ctypes.windll.LoadLibrary(self.dll_path)
            self.inpout.IsInpOutDriverOpen.restype = ctypes.c_int
            self.inpout.Out32.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
            self.inpout.Inp32.argtypes = [ctypes.c_ushort]
            self.inpout.Inp32.restype = ctypes.c_ushort
            self.is_initialized = bool(self.inpout.IsInpOutDriverOpen())
        except: self.is_initialized = False

    def _wait_ibf(self):
        timeout = 0.1
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            if not (self.inpout.Inp32(EC_SC) & EC_IBF): return True
            time.sleep(0.001) # <--- CRITICAL FIX
        return False

    def _wait_obf(self):
        timeout = 0.1
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            if (self.inpout.Inp32(EC_SC) & EC_OBF): return True
            time.sleep(0.001) # <--- CRITICAL FIX
        return False

    def read_register(self, reg):
        if not self.is_initialized: return None
        with self.lock: # Thread safety
            if not self._wait_ibf(): return None
            self.inpout.Out32(EC_SC, EC_CMD_READ)
            if not self._wait_ibf(): return None
            self.inpout.Out32(EC_DATA, reg)
            if not self._wait_obf(): return None
            return self.inpout.Inp32(EC_DATA)

    def write_register(self, reg, val):
        if not self.is_initialized: return False
        with self.lock:
            if not self._wait_ibf(): return False
            self.inpout.Out32(EC_SC, EC_CMD_WRITE)
            if not self._wait_ibf(): return False
            self.inpout.Out32(EC_DATA, reg)
            if not self._wait_ibf(): return False
            self.inpout.Out32(EC_DATA, val)
            return True
