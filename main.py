import ctypes
import xml.etree.ElementTree as ET
import os
import time
import sys
import threading
from tkinter import messagebox

from ui.main_window import MainWindow
from config import AppConfig
from fan_controller import FanController, PsutilTempSensor
from plugin_manager import PluginManager
from system_tray import SystemTray
import themes
import localization

if sys.platform == 'win32':
    import winreg

# --- EC CONSTANTS (ACPI Standard) ---
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
        self.is_initialized = self._load_driver()

    def _load_driver(self):
        if not os.path.exists(self.dll_path):
            print(f"Error: {self.dll_path} not found")
            return False
        try:
            self.inpout = ctypes.windll.LoadLibrary(self.dll_path)
            self.inpout.IsInpOutDriverOpen.restype = ctypes.c_int
            self.inpout.Out32.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
            self.inpout.Inp32.argtypes = [ctypes.c_ushort]
            self.inpout.Inp32.restype = ctypes.c_ushort

            if not self.inpout.IsInpOutDriverOpen():
                return False
            return True
        except (OSError, AttributeError) as e:
            print(f"Driver load error: {e}")
            return False

    def _wait_ibf(self):
        timeout = 0.1
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            status = self.inpout.Inp32(EC_SC)
            if not (status & EC_IBF):
                return True
            pass
        return False

    def _wait_obf(self):
        timeout = 0.1
        start = time.perf_counter()
        while (time.perf_counter() - start) < timeout:
            status = self.inpout.Inp32(EC_SC)
            if (status & EC_OBF):
                return True
            pass
        return False

    def read_register(self, register):
        if not self.is_initialized: return None
        if not self._wait_ibf(): return None
        self.inpout.Out32(EC_SC, EC_CMD_READ)
        if not self._wait_ibf(): return None
        self.inpout.Out32(EC_DATA, register)
        if not self._wait_obf(): return None
        return self.inpout.Inp32(EC_DATA)

    def write_register(self, register, value):
        if not self.is_initialized: return False
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
        self.model_name = "No config loaded"

    def parse(self):
        if not self.file or not os.path.exists(self.file):
            return False
        try:
            tree = ET.parse(self.file)
            root = tree.getroot()
            model_node = root.find('NotebookModel')
            if model_node is not None:
                self.model_name = model_node.text
            self.fans.clear()
            for fan_config in root.findall('.//FanConfiguration'):
                name_node = fan_config.find('Name')
                fan_name = name_node.text if name_node is not None else 'Unnamed Fan'
                fan = {
                    'name': fan_name,
                    'read_reg': int(fan_config.find('ReadRegister').text),
                    'write_reg': int(fan_config.find('WriteRegister').text),
                    'min_speed': int(fan_config.find('MinSpeedValue').text),
                    'max_speed': int(fan_config.find('MaxSpeedValue').text),
                    'temp_thresholds': []
                }
                thresholds_node = fan_config.find('TemperatureThresholds')
                if thresholds_node is not None:
                    for threshold in thresholds_node.findall('TemperatureThreshold'):
                        up = int(threshold.find('UpThreshold').text)
                        down = int(threshold.find('DownThreshold').text)
                        speed = int(float(threshold.find('FanSpeed').text))
                        fan['temp_thresholds'].append((up, down, speed))
                self.fans.append(fan)
            return True
        except ET.ParseError:
            return False


class AppLogic:
    def __init__(self):
        self.config = AppConfig()
        self.driver = EcDriver()
        self.nbfc_parser = NbfcConfigParser(None)
        self.stop_event = threading.Event()
        self.update_thread = None
        self.temp_sensor = PsutilTempSensor()
        self.fan_controller = FanController(self, self.temp_sensor)
        self.system_tray = SystemTray(self)

        # Setup localization
        localization.set_language(self.config.get("language"))

        self.main_window = MainWindow(self)

        # Apply theme now that the window exists
        self.apply_theme(self.config.get("theme"))

        self._load_last_config()

        # Initialize Plugin Manager
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
        self.fan_controller.start()

    def apply_theme(self, theme_name):
        self.config.set("theme", theme_name)
        if hasattr(self, 'main_window'):
            themes.apply_theme(self.main_window, theme_name)

    def set_language(self, lang_code):
        self.config.set("language", lang_code)
        localization.set_language(lang_code)
        self.main_window.recreate_ui()

    def _load_config(self, filepath):
        if self.update_thread and self.update_thread.is_alive():
            self.stop_event.set()
            self.update_thread.join(timeout=1.0)

        parser = NbfcConfigParser(filepath)
        if parser.parse():
            self.nbfc_parser = parser
            self.config.set("last_config_path", filepath)
            self.main_window.model_label.config(text=f"Model: {self.nbfc_parser.model_name}")
            self.main_window.create_fan_widgets(self.nbfc_parser.fans)

            self.stop_event.clear()
            self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
            self.update_thread.start()
        else:
            self.config.set("last_config_path", None)
            self.nbfc_parser = NbfcConfigParser(None)
            self.main_window.model_label.config(text="Model: No config loaded")
            self.main_window.create_fan_widgets([]) # Clear fan widgets

    def _load_last_config(self):
        last_config = self.config.get("last_config_path")
        if last_config:
            self._load_config(last_config)

    def load_config_file(self):
        filepath = self.main_window.get_selected_filepath()
        if filepath:
            self._load_config(filepath)

    def set_fan_speed(self, fan_index):
        slider_var = self.main_window.fan_vars.get(f'fan_{fan_index}_write')
        if not slider_var:
            return

        fan = self.nbfc_parser.fans[fan_index]
        min_val = fan['min_speed']
        max_val = fan['max_speed']
        disabled_val = min_val - 2
        read_only_val = min_val - 1
        auto_val = max_val + 1

        # If the slider is set to "Auto", "Read-only", or "Disabled", we don't do anything here.
        if slider_var.get() in (auto_val, read_only_val, disabled_val):
            return

        self.set_fan_speed_internal(fan_index, slider_var.get())

    def set_fan_speed_internal(self, fan_index, speed):
        threading.Thread(target=self._set_fan_speed_thread, args=(fan_index, speed)).start()

    def _set_fan_speed_thread(self, fan_index, speed):
        fan = self.nbfc_parser.fans[fan_index]
        write_reg = fan['write_reg']
        self.driver.write_register(write_reg, speed)

    def update_loop(self):
        while not self.stop_event.is_set():
            if self.nbfc_parser and self.nbfc_parser.fans:
                for i, fan in enumerate(self.nbfc_parser.fans):
                    slider_var = self.main_window.fan_vars.get(f'fan_{i}_write')
                    if not slider_var:
                        continue

                    min_val = fan['min_speed']
                    disabled_val = min_val - 2

                    if slider_var.get() != disabled_val:
                        read_reg = fan['read_reg']
                        value = self.driver.read_register(read_reg)
                        if value is not None:
                            self.main_window.update_fan_readings(i, value)
            self.stop_event.wait(2.0)

    def on_closing(self):
        # Hide the window instead of closing it
        self.main_window.withdraw()

    def quit(self):
        self.stop_event.set()
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
        self.fan_controller.stop()
        self.plugin_manager.shutdown_plugins()
        self.system_tray.icon.stop()
        self.main_window.quit()

    def run(self):
        if sys.platform == 'win32':
            self.system_tray.create_icon()

        if '--start-in-tray' in sys.argv and sys.platform == 'win32':
            self.main_window.withdraw()
        else:
            self.main_window.deiconify()

        self.main_window.mainloop()

    def toggle_autostart(self):
        autostart = self.main_window.autostart_var.get()
        self.config.set("autostart", autostart)

        if sys.platform == 'win32':
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "VortECIO"

            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                if autostart:
                    executable_path = sys.executable
                    # If running from a bundled executable, sys.executable is the path to the exe
                    # If running from a script, we need to build the command
                    if executable_path.endswith("python.exe") or executable_path.endswith("pythonw.exe"):
                         script_path = os.path.abspath(__file__)
                         value = f'"{executable_path}" "{script_path}" --start-in-tray'
                    else: # Assuming bundled executable
                        value = f'"{executable_path}" --start-in-tray'

                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
                else:
                    winreg.DeleteValue(key, app_name)
                winreg.CloseKey(key)
            except OSError as e:
                print(f"Failed to update registry for autostart: {e}")


def main():
    if sys.platform == 'win32':
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except AttributeError:
            is_admin = False
        if not is_admin:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)

    app = AppLogic()
    app.run()


if __name__ == "__main__":
    main()
