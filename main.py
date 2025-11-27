import ctypes
import xml.etree.ElementTree as ET
import os
import logging
from logger import setup_logger, get_logger
import time
import sys
import threading
from tkinter import messagebox
from typing import List, Dict, Any, Optional, Tuple

from hardware import EcDriver
from ui.main_window import MainWindow
from config import AppConfig
from fan_controller import FanController
from plugin_manager import PluginManager
import customtkinter as ctk
import themes
import localization

if sys.platform == 'win32':
    import wmi
    import pythoncom
    from system_tray import SystemTray
from concurrent.futures import ThreadPoolExecutor

if sys.platform == 'win32':
    import winreg



class NbfcConfigParser:
    def __init__(self, xml_file: Optional[str]) -> None:
        self.file: Optional[str] = xml_file
        self.fans: List[Dict[str, Any]] = []
        self.model_name: str = "No config loaded"
        self.ec_poll_interval: int = 3000
        self.read_write_words: bool = False
        self.critical_temperature: float = 90.0
        self.ec_data_port: int = 0x62
        self.ec_command_port: int = 0x66
        self.register_write_mode: str = 'Set'

    def parse(self) -> bool:
        if not self.file or not os.path.exists(self.file):
            return False
        try:
            tree = ET.parse(self.file)
            root = tree.getroot()
            model_node = root.find('NotebookModel')
            if model_node is not None and model_node.text is not None:
                self.model_name = model_node.text

            poll_interval_node = root.find('EcPollInterval')
            if poll_interval_node is not None and poll_interval_node.text:
                self.ec_poll_interval = int(poll_interval_node.text)

            read_write_words_node = root.find('ReadWriteWords')
            if read_write_words_node is not None and read_write_words_node.text:
                self.read_write_words = read_write_words_node.text.lower() == 'true'

            critical_temp_node = root.find('CriticalTemperature')
            if critical_temp_node is not None and critical_temp_node.text:
                self.critical_temperature = float(critical_temp_node.text)
                logging.info(f"Critical temperature: {self.critical_temperature}°C")

            ec_io_ports = root.find('EcIoPorts')
            if ec_io_ports is not None:
                data_port = ec_io_ports.find('DataPort')
                cmd_port = ec_io_ports.find('CommandPort')
                if data_port is not None and data_port.text:
                    self.ec_data_port = int(data_port.text, 0)
                if cmd_port is not None and cmd_port.text:
                    self.ec_command_port = int(cmd_port.text, 0)

            write_mode_node = root.find('RegisterWriteMode')
            if write_mode_node is not None and write_mode_node.text:
                self.register_write_mode = write_mode_node.text

            self.fans.clear()
            for fan_config in root.findall('.//FanConfiguration'):
                fan_name = 'Unnamed Fan'
                display_name_node = fan_config.find('FanDisplayName')
                if display_name_node is not None and display_name_node.text:
                    fan_name = display_name_node.text
                else:
                    name_node = fan_config.find('Name')
                    if name_node is not None and name_node.text:
                        fan_name = name_node.text

                reset_val_node = fan_config.find('FanSpeedResetValue')
                reset_val = int(reset_val_node.text) if reset_val_node is not None and reset_val_node.text else 255

                min_speed = int(fan_config.find('MinSpeedValue').text)
                max_speed = int(fan_config.find('MaxSpeedValue').text)

                fan: Dict[str, Any] = {
                    'name': fan_name,
                    'read_reg': int(fan_config.find('ReadRegister').text),
                    'write_reg': int(fan_config.find('WriteRegister').text),
                    'min_speed': min_speed,
                    'max_speed': max_speed,
                    'reset_val': reset_val,
                    'is_inverted': min_speed > max_speed,
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
        except (ET.ParseError, ValueError, TypeError) as e:
            logging.error(f"Failed to parse NBFC config: {e}")
            return False


if sys.platform == 'win32':
    class WmiTempSensor:
        def __init__(self) -> None:
            self.w: Optional[wmi.WMI] = None
            try:
                pythoncom.CoInitialize()
                self.w = wmi.WMI(namespace="root\\wmi")
            except Exception as e:
                logging.error(f"Failed to initialize WMI: {e}")

        def get_temperature(self) -> float:
            if not self.w:
                return 45.0
            try:
                temps = self.w.MSAcpi_ThermalZoneTemperature()
                max_t = 0.0
                for t in temps:
                    c = (t.CurrentTemperature - 2732) / 10.0
                    if c > max_t:
                        max_t = c
                return max_t if max_t > 20.0 else 45.0
            except Exception:
                return 45.0

        def get_temperatures(self) -> Tuple[Optional[float], Optional[float]]:
            return self.get_temperature(), None

        def shutdown(self) -> None:
            pythoncom.CoUninitialize()
else:
    class WmiTempSensor:
        def __init__(self) -> None:
            logging.info("Running on non-Windows OS, WMI sensor is disabled.")
        def get_temperature(self) -> float:
            return 45.0
        def get_temperatures(self) -> Tuple[Optional[float], Optional[float]]:
            return 45.0, None
        def shutdown(self) -> None:
            pass


class AppLogic:
    def __init__(self) -> None:
        self.config: AppConfig = AppConfig()
        self.driver: EcDriver = EcDriver()
        self.nbfc_parser: NbfcConfigParser = NbfcConfigParser(None)
        self.stop_event: threading.Event = threading.Event()
        self.default_sensor: WmiTempSensor = WmiTempSensor()
        self.plugin_sensor: Optional[Any] = None
        self.fan_controller: FanController = FanController(self)
        self.fan_control_disabled: bool = False

        if sys.platform == 'win32':
            self.system_tray: Optional[SystemTray] = SystemTray(self)
        else:
            self.system_tray = None

        localization.set_language(self.config.get("language"))
        self.main_window: MainWindow = MainWindow(self)
        self.apply_theme(self.config.get("theme"))
        self.main_window.after(100, self.start_background_tasks)

    def start_background_tasks(self) -> None:
        self._load_last_config()
        self.plugin_manager: PluginManager = PluginManager(self)
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
        self.fan_controller.start()

    def get_active_sensor(self) -> Any:
        return self.plugin_sensor if self.plugin_sensor else self.default_sensor

    def register_sensor(self, sensor_instance: Any) -> None:
        logging.info(f"New sensor registered: {sensor_instance}")
        self.plugin_sensor = sensor_instance

    def apply_theme(self, theme_name: str) -> None:
        self.config.set("theme", theme_name)
        valid_themes = ["light", "dark", "system"]
        if theme_name in valid_themes:
            ctk.set_appearance_mode(theme_name)

    def set_language(self, lang_code: str) -> None:
        self.config.set("language", lang_code)
        localization.set_language(lang_code)
        self.main_window.recreate_ui()

    def _load_config(self, filepath: str) -> None:
        if self.update_thread and self.update_thread.is_alive():
            self.stop_event.set()
            self.update_thread.join(timeout=1.0)

        parser = NbfcConfigParser(filepath)
        if parser.parse():
            for fan in parser.fans:
                fan['temp_thresholds'].sort(key=lambda x: x[0])
            self.nbfc_parser = parser
            self.fan_controller.critical_temperature = parser.critical_temperature
            self.config.set("last_config_path", filepath)
            if parser.ec_data_port != 0x62 or parser.ec_command_port != 0x66:
                self.driver = EcDriver(ec_data_port=parser.ec_data_port, ec_command_port=parser.ec_command_port)
                logging.info(f"EC driver reinitialized: Data=0x{parser.ec_data_port:02X}, Cmd=0x{parser.ec_command_port:02X}")
            self.main_window.model_label.configure(text=f"Model: {self.nbfc_parser.model_name}")
            self.main_window.create_fan_widgets(self.nbfc_parser.fans)
        else:
            self.config.set("last_config_path", None)
            self.nbfc_parser = NbfcConfigParser(None)
            self.main_window.model_label.configure(text="Model: No config loaded")
            self.main_window.create_fan_widgets([])

    def _load_last_config(self) -> None:
        last_config = self.config.get("last_config_path")
        if last_config:
            self._load_config(last_config)

    def load_config_file(self) -> None:
        filepath = self.main_window.get_selected_filepath()
        if filepath:
            self._load_config(filepath)

    def set_fan_speed(self, fan_index: int) -> None:
        slider_var = self.main_window.fan_vars.get(f'fan_{fan_index}_write')
        if not slider_var:
            return
        fan = self.nbfc_parser.fans[fan_index]
        min_val, max_val = fan['min_speed'], fan['max_speed']
        disabled_val, read_only_val = min_val - 2, min_val - 1
        auto_val = max_val + 1
        if slider_var.get() in (auto_val, read_only_val, disabled_val):
            return
        self.set_fan_speed_internal(fan_index, slider_var.get())

    def set_fan_speed_internal(self, fan_index: int, speed: int, force_write: bool = False) -> None:
        if self.fan_control_disabled:
            return
        if not force_write:
            slider_var = self.main_window.fan_vars.get(f'fan_{fan_index}_write')
            if not slider_var:
                return
            fan = self.nbfc_parser.fans[fan_index]
            min_val = fan['min_speed']
            disabled_val, read_only_val = min_val - 2, min_val - 1
            if slider_var.get() in (read_only_val, disabled_val):
                return
        threading.Thread(target=self._set_fan_speed_thread, args=(fan_index, speed)).start()

    def _set_fan_speed_thread(self, fan_index: int, speed: int) -> None:
        if self.fan_control_disabled:
            return
        fan = self.nbfc_parser.fans[fan_index]
        write_reg = fan['write_reg']
        self.fan_controller.set_last_speed(fan_index, speed)
        self.driver.write_register(write_reg, speed)

    def on_closing(self) -> None:
        self.main_window.withdraw()

    def quit(self) -> None:
        self.stop_event.set()
        self.fan_controller.stop()
        self.plugin_manager.shutdown_plugins()
        if isinstance(self.default_sensor, WmiTempSensor):
            self.default_sensor.shutdown()
        self.config._flush_changes()
        if self.system_tray and self.system_tray.icon:
            self.system_tray.icon.stop()
        self.main_window.quit()

    def run(self) -> None:
        if sys.platform == 'win32':
            threading.Thread(target=self.system_tray.create_icon, daemon=True).start()
        if '--start-in-tray' in sys.argv and sys.platform == 'win32':
            self.main_window.withdraw()
        else:
            self.main_window.deiconify()
        self.main_window.mainloop()

    def toggle_autostart(self) -> None:
        autostart = self.main_window.autostart_var.get()
        self.config.set("autostart", autostart)
        if sys.platform == 'win32':
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "VortECIO"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                if autostart:
                    executable_path = sys.executable
                    if executable_path.endswith(("python.exe", "pythonw.exe")):
                        script_path = os.path.abspath(__file__)
                        value = f'"{executable_path}" "{script_path}" --start-in-tray'
                    else:
                        value = f'"{executable_path}" --start-in-tray'
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
                else:
                    winreg.DeleteValue(key, app_name)
                winreg.CloseKey(key)
            except OSError as e:
                logging.error(f"Failed to update registry for autostart: {e}")


from utils import normalize_fan_speed

def unblock_file(filepath: str) -> None:
    if sys.platform != 'win32':
        return
    ads_path = filepath + ":Zone.Identifier"
    try:
        if os.path.exists(ads_path):
            os.remove(ads_path)
            logging.info(f"Unblocked {os.path.basename(filepath)}")
    except OSError as e:
        logging.warning(f"Failed to unblock {os.path.basename(filepath)}: {e}")


def main() -> None:
    setup_logger()
    if sys.platform == 'win32':
        unblock_file('inpoutx64.dll')
        unblock_file('plugins/lhm_sensor/LibreHardwareMonitorLib.dll')
        unblock_file('plugins/lhm_sensor/HidSharp.dll')
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
