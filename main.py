import ctypes
import xml.etree.ElementTree as ET
import os
import time
import sys

# --- CONFIGURATION ---
XML_CONFIG_FILE = 'HP-Pavilion-Gaming-Laptop-15-ec2xxx.xml'
DLL_NAME = 'inpoutx64.dll'

# --- EC CONSTANTS (ACPI Standard) ---
EC_SC = 0x66  # Status/Command Port
EC_DATA = 0x62 # Data Port
EC_CMD_READ = 0x80
EC_CMD_WRITE = 0x81
EC_IBF = 0x02 # Input Buffer Full mask
EC_OBF = 0x01 # Output Buffer Full mask

class EcDriver:
    def __init__(self, dll_path):
        self.dll_path = dll_path
        self.inpout = None
        self._load_driver()

    def _load_driver(self):
        if not os.path.exists(self.dll_path):
            print(f"[ERROR] {self.dll_path} not found! Download it via Highrez InpOut.")
            sys.exit(1)
        try:
            self.inpout = ctypes.windll.LoadLibrary(self.dll_path)
            # Налаштування типів аргументів для безпеки
            self.inpout.IsInpOutDriverOpen.restype = ctypes.c_int
            self.inpout.Out32.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
            self.inpout.Inp32.argtypes = [ctypes.c_ushort]
            self.inpout.Inp32.restype = ctypes.c_ushort
            
            if not self.inpout.IsInpOutDriverOpen():
                print("[ERROR] Driver not opened. Run as Administrator!")
                sys.exit(1)
            print("[OK] Driver InpOutx64 initialized successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load driver: {e}")
            sys.exit(1)

    def _wait_ibf(self):
        """Wait for Input Buffer to be empty (ready for command)"""
        for _ in range(1000):
            status = self.inpout.Inp32(EC_SC)
            if not (status & EC_IBF):
                return True
            time.sleep(0.001)
        return False

    def _wait_obf(self):
        """Wait for Output Buffer to be full (ready to read data)"""
        for _ in range(1000):
            status = self.inpout.Inp32(EC_SC)
            if (status & EC_OBF):
                return True
            time.sleep(0.001)
        return False

    def read_register(self, register):
        if not self._wait_ibf(): return None
        self.inpout.Out32(EC_SC, EC_CMD_READ)
        
        if not self._wait_ibf(): return None
        self.inpout.Out32(EC_DATA, register)
        
        if not self._wait_obf(): return None
        return self.inpout.Inp32(EC_DATA)

    def write_register(self, register, value):
        if not self._wait_ibf(): return False
        self.inpout.Out32(EC_SC, EC_CMD_WRITE)
        
        if not self._wait_ibf(): return False
        self.inpout.Out32(EC_DATA, register)
        
        if not self._wait_ibf(): return False
        self.inpout.Out32(EC_DATA, value)
        return True

class NbfcConfigParser:
    def __init__(self, xml_file):
        self.file = xml_file
        self.fans = []
        self.model_name = "Unknown"

    def parse(self):
        try:
            tree = ET.parse(self.file)
            root = tree.getroot()
            
            # Get Model Name
            model_node = root.find('NotebookModel')
            if model_node is not None:
                self.model_name = model_node.text

            # Get Fans
            for fan_config in root.findall('.//FanConfiguration'):
                fan = {
                    'read_reg': int(fan_config.find('ReadRegister').text),
                    'write_reg': int(fan_config.find('WriteRegister').text),
                    'min_speed': int(fan_config.find('MinSpeedValue').text),
                    'max_speed': int(fan_config.find('MaxSpeedValue').text),
                    # Можна додати Reset регистри, якщо вони є в XML
                }
                self.fans.append(fan)
            
            print(f"[OK] Parsed config for: {self.model_name}")
            print(f"[INFO] Found {len(self.fans)} fan configurations.")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to parse XML: {e}")
            return False

# --- MAIN APP ---
def main():
    print("=== VortEC: Python NBFC Player ===")
    
    # 1. Load Config
    config = NbfcConfigParser(XML_CONFIG_FILE)
    if not config.parse():
        return

    # 2. Init Driver
    driver = EcDriver(DLL_NAME)

    print("\nStarting Monitoring (Press Ctrl+C to stop)...")
    print(f"{'Fan ID':<10} | {'Read Reg':<10} | {'Value (0-255)':<15} | {'Write Reg':<10}")
    print("-" * 55)

    try:
        while True:
            # Лише читання для тесту (безпечний режим)
            for idx, fan in enumerate(config.fans):
                val = driver.read_register(fan['read_reg'])
                val_str = f"{val}" if val is not None else "ERR"
                
                # Виводимо інфо
                # \r дозволяє оновлювати рядок в консолі
                print(f"Fan #{idx+1:<5} | {fan['read_reg']:<10} | {val_str:<15} | {fan['write_reg']:<10}")
            
            # --- ТУТ МОЖНА ДОДАТИ ЛОГІКУ КЕРУВАННЯ ---
            # Наприклад:
            # if cpu_temp > 70:
            #     driver.write_register(fan['write_reg'], 255) # Max speed
            
            print("-" * 55)
            time.sleep(2) # NBFC Poll Interval (зазвичай 500-3000мс)
            
    except KeyboardInterrupt:
        print("\n[STOP] Exiting...")

if __name__ == "__main__":
    # Перевірка на адміна
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("[WARN] Restarting as Administrator...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    else:
        main()
