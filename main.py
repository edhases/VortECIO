import ctypes
import xml.etree.ElementTree as ET
import os
import logging
from logger import setup_logger, get_logger
import time
import sys
import threading
from typing import List, Dict, Any, Optional, Tuple

from hardware import EcDriver
from ui.main_window import MainWindow
from config import AppConfig
from fan_controller import FanController
from plugin_manager import PluginManager
import customtkinter as ctk
import tkinter as tk
import localization
from utils import denormalize_fan_speed
from advanced_logging import init_detailed_logging, get_detailed_logger

if sys.platform == 'win32':
    import wmi
    import pythoncom
    from system_tray import SystemTray


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

    @staticmethod
    def _to_int(value: str) -> int:
        """Convert XML value to int, supporting floats and hex."""
        try:
            return int(value, 0)  # Handles '123' and '0xFF'
        except (ValueError, TypeError):
            return int(float(value))  # Handles '123.0'

    def parse(self) -> bool:
        if not self.file or not os.path.exists(self.file):
            return False
        try:
            tree = ET.parse(self.file)
            root = tree.getroot()
            model_node = root.find('NotebookModel')
            if model_node is not None and model_node.text is not None:
                self.model_name = model_node.text

            # Validate poll interval (100ms - 10s is safe range)
            poll_interval_node = root.find('.//EcPollInterval')
            if poll_interval_node is not None and poll_interval_node.text:
                poll_interval = self._to_int(poll_interval_node.text)
                if not (100 <= poll_interval <= 10000):
                    raise ValueError(f"Invalid ec_poll_interval: {poll_interval}. Must be 100-10000 ms.")
                self.ec_poll_interval = poll_interval

            read_write_words_node = root.find('ReadWriteWords')
            if read_write_words_node is not None and read_write_words_node.text:
                self.read_write_words = read_write_words_node.text.lower() == 'true'

            # Validate critical temperature (0-150°C reasonable range)
            critical_temp_node = root.find('.//CriticalTemperature')
            if critical_temp_node is not None and critical_temp_node.text is not None:
                critical_temp = float(critical_temp_node.text)
                if not (0 <= critical_temp <= 150):
                    raise ValueError(f"Invalid critical_temperature: {critical_temp}. Must be 0-150°C.")
                self.critical_temperature = critical_temp

            ec_io_ports = root.find('EcIoPorts')
            if ec_io_ports is not None:
                data_port = ec_io_ports.find('DataPort')
                cmd_port = ec_io_ports.find('CommandPort')
                if data_port is not None and data_port.text:
                    self.ec_data_port = self._to_int(data_port.text)
                if cmd_port is not None and cmd_port.text:
                    self.ec_command_port = self._to_int(cmd_port.text)

            write_mode_node = root.find('RegisterWriteMode')
            if write_mode_node is not None and write_mode_node.text:
                self.register_write_mode = write_mode_node.text

            self.fans.clear()
            # Validate fan speeds (0-255 for EC registers)
            for fan_node in root.findall('.//FanConfiguration'):
                min_speed = self._to_int(fan_node.find('MinSpeedValue').text)
                max_speed = self._to_int(fan_node.find('MaxSpeedValue').text)

                # Validate range
                if not (0 <= min_speed <= 255):
                    raise ValueError(f"Invalid min_speed: {min_speed}. Must be 0-255.")
                if not (0 <= max_speed <= 255):
                    raise ValueError(f"Invalid max_speed: {max_speed}. Must be 0-255.")

                # Validate register addresses (EC typically uses 0x00-0xFF)
                read_reg = self._to_int(fan_node.find('ReadRegister').text)
                write_reg = self._to_int(fan_node.find('WriteRegister').text)
                if not (0x00 <= read_reg <= 0xFF):
                    raise ValueError(f"Invalid read_reg: 0x{read_reg:X}. Must be 0x00-0xFF.")
                if not (0x00 <= write_reg <= 0xFF):
                    raise ValueError(f"Invalid write_reg: 0x{write_reg:X}. Must be 0x00-0xFF.")

                fan_name = 'Unnamed Fan'
                display_name_node = fan_node.find('FanDisplayName')
                if display_name_node is not None and display_name_node.text:
                    fan_name = display_name_node.text
                else:
                    name_node = fan_node.find('Name')
                    if name_node is not None and name_node.text:
                        fan_name = name_node.text

                reset_val_node = fan_node.find('FanSpeedResetValue')
                reset_val = self._to_int(reset_val_node.text) if reset_val_node is not None and reset_val_node.text else 255

                # --- NEW NBFC FIELDS START ---
                min_speed_read_node = fan_node.find('MinSpeedValueRead')
                min_speed_read = self._to_int(min_speed_read_node.text) if min_speed_read_node is not None and min_speed_read_node.text else 0

                max_speed_read_node = fan_node.find('MaxSpeedValueRead')
                max_speed_read = self._to_int(max_speed_read_node.text) if max_speed_read_node is not None and max_speed_read_node.text else 0

                independent_read_node = fan_node.find('IndependentReadMinMaxValues')
                independent_read = False
                if independent_read_node is not None and independent_read_node.text:
                    independent_read = independent_read_node.text.lower() == 'true'
                # --- NEW NBFC FIELDS END ---

                # Store validated values
                fan: Dict[str, Any] = {
                    'name': fan_name,
                    'read_reg': read_reg,
                    'write_reg': write_reg,
                    'min_speed': min_speed,
                    'max_speed': max_speed,
                    # Add new fields to fan config dict
                    'min_speed_read': min_speed_read,
                    'max_speed_read': max_speed_read,
                    'independent_read_min_max': independent_read,
                    'reset_val': reset_val,
                    'is_inverted': min_speed > max_speed,
                    'temp_thresholds': []
                }

                # Validate temperature thresholds in fan curves
                for threshold in fan_node.findall('.//TemperatureThreshold'):
                    up_temp = self._to_int(threshold.find('UpThreshold').text)
                    down_temp = self._to_int(threshold.find('DownThreshold').text)
                    fan_speed = self._to_int(threshold.find('FanSpeed').text)

                    if not (0 <= up_temp <= 150):
                        raise ValueError(f"Invalid up_temp: {up_temp}. Must be 0-150°C.")
                    if not (0 <= down_temp <= 150):
                        raise ValueError(f"Invalid down_temp: {down_temp}. Must be 0-150°C.")
                    if down_temp >= up_temp:
                        raise ValueError(f"down_temp must be < up_temp (hysteresis logic).")
                    if not (0 <= fan_speed <= 100):
                        raise ValueError(f"Invalid fan_speed: {fan_speed}. Must be 0-100%.")
                    fan['temp_thresholds'].append((up_temp, down_temp, fan_speed))

                self.fans.append(fan)

            return True

        except ValueError as e:
            logging.error(f"XML validation failed: {e}")
            return False
        except (ET.ParseError, TypeError, AttributeError) as e:
            logging.error(f"Failed to parse config: {e}")
            return False


if sys.platform == 'win32':
    class WmiTempSensor:
        def __init__(self) -> None:
            """Initializes the WMI sensor in a thread-safe manner."""
            # COM objects are initialized on-demand in the calling thread
            # to prevent cross-thread marshalling errors.
            pass

        def get_temperatures(self) -> Tuple[Optional[float], Optional[float]]:
            """
            Fetches CPU temperature from WMI.
            This method is thread-safe.
            """
            try:
                pythoncom.CoInitialize()
                w = wmi.WMI(namespace="root\\wmi")
                temps = w.MSAcpi_ThermalZoneTemperature()

                if not temps:
                    logging.warning("WMI: No MSAcpi_ThermalZoneTemperature sensors found.")
                    return None, None

                max_t = 0.0
                for t in temps:
                    # Temp is in tenths of Kelvin, convert to Celsius
                    c = (t.CurrentTemperature - 2732) / 10.0
                    if c > max_t:
                        max_t = c

                temp_result = max_t if max_t > 0 else None
                return temp_result, None

            except wmi.x_wmi as e:
                logging.error(f"WMI query failed: {e}")
                return None, None
            except pythoncom.com_error as e:
                logging.error(f"COM error during WMI query, likely a threading issue: {e}")
                return None, None
            finally:
                pythoncom.CoUninitialize()

        def shutdown(self) -> None:
            # No-op, CoUninitialize is called in get_temperatures
            pass
else:
    class WmiTempSensor:
        def __init__(self) -> None:
            logging.info("Running on non-Windows OS, WMI sensor is disabled.")
        def get_temperatures(self) -> Tuple[Optional[float], Optional[float]]:
            # Return a dummy value for testing on non-windows
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

        # Initialize detailed logging from config
        detailed_logging_enabled = self.config.get("detailed_logging", False)
        init_detailed_logging(detailed_logging_enabled)

        # Update regular logger level based on detailed logging
        if detailed_logging_enabled:
            logging.getLogger('FanControl').setLevel(logging.DEBUG)

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
        """Get active temperature sensor (prefer LHM over WMI)."""
        # Try LHM first if available and preferred
        if self.plugin_sensor and self.config.get("prefer_lhm", True):
            return self.plugin_sensor
        # Fallback to WMI
        return self.default_sensor

    def register_sensor(self, sensor_instance: Any) -> None:
        logging.info(f"New sensor registered: {sensor_instance}")
        self.plugin_sensor = sensor_instance

    def apply_theme(self, theme: str):
        self.config.set('theme', theme)
        ctk.set_appearance_mode(theme)

        # Close Settings window (CTkToplevel has theme change bugs)
        if hasattr(self.main_window, 'settings_window'):
            try:
                if self.main_window.settings_window.winfo_exists():
                    self.main_window.settings_window.destroy()
                    # Show notification
                    from ui.main_window import StatusNotification
                    StatusNotification(
                        self.main_window,
                        f"Theme changed. Reopen Settings if needed.",
                        duration=3000
                    )
            except (AttributeError, tk.TclError):
                # This can happen if the window is already destroyed. Safe to ignore.
                pass

    def set_language(self, lang_code: str):
        self.config.set('language', lang_code)
        localization.set_language(lang_code)

        # Recreate entire UI to apply new language strings
        if hasattr(self, 'main_window') and self.main_window.winfo_exists():
            # Close any child windows first
            for widget in self.main_window.winfo_children():
                if isinstance(widget, ctk.CTkToplevel):
                    widget.destroy()
            self.main_window.recreate_ui()

        # Close outdated settings window
        if hasattr(self.main_window, 'settings_window'):
            try:
                if self.main_window.settings_window.winfo_exists():
                    self.main_window.settings_window.destroy()
            except (AttributeError, tk.TclError):
                # This can happen if the window is already destroyed. Safe to ignore.
                pass

    def _load_config(self, filepath: str) -> None:
        parser = NbfcConfigParser(filepath)
        if parser.parse():
            for fan in parser.fans:
                fan['temp_thresholds'].sort(key=lambda x: x[0])
            self.nbfc_parser = parser

            # Log config load
            detailed_logger = get_detailed_logger()
            if detailed_logger:
                detailed_logger.log_config_loaded(
                    model=parser.model_name,
                    fans=len(parser.fans),
                    critical_temp=parser.critical_temperature
                )

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

    def set_manual_fan_speed(self, fan_index: int, speed_percent: int) -> None:
        """
        Set fan to manual speed (percentage 0-100).
        Args:
            fan_index: Fan index
            speed_percent: Target speed percentage (0-100)
        """
        fan = self.nbfc_parser.fans[fan_index]
        # Convert percentage to raw EC value
        raw_speed = denormalize_fan_speed(speed_percent, fan)
        # Apply immediately
        self.set_fan_speed_internal(fan_index, raw_speed)

    def set_fan_mode(self, fan_index: int, mode: str):
        """
        Set fan control mode.
        Args:
            mode: 'Auto', 'Manual', 'Read-only', 'Disabled'
        """
        if not (0 <= fan_index < len(self.nbfc_parser.fans)):
            return
        fan = self.nbfc_parser.fans[fan_index]

        mode_mapping = {
            'Auto': fan['max_speed'] + 1,
            'Manual': -1,  # Special: will use slider value
            'Read-only': fan['min_speed'] - 1,
            'Disabled': fan['min_speed'] - 2
        }

        internal_value = mode_mapping[mode]

        # For Manual mode, read from slider
        if mode == 'Manual':
            slider_var = self.main_window.fan_slider_vars.get(fan_index)
            if slider_var:
                internal_value = slider_var.get()

        self.fan_controller.set_fan_mode_cached(fan_index, internal_value)

        if mode == 'Disabled':
            # Write reset value immediately
            self.set_fan_speed_internal(fan_index, fan['reset_val'], force_write=True)

    def set_fan_speed_internal(self, fan_index: int, speed: int, force_write: bool = False) -> None:
        if self.fan_control_disabled:
            return

        if not force_write:
            # Check mode from new UI structure
            mode_var = self.main_window.fan_mode_vars.get(fan_index)
            if mode_var:
                mode = mode_var.get()
                # Don't write if in read-only or disabled mode
                if mode in ('Read-only', 'Disabled'):
                    return

        threading.Thread(target=self._set_fan_speed_thread, args=(fan_index, speed)).start()

    def _set_fan_speed_thread(self, fan_index: int, speed: int) -> None:
        if self.fan_control_disabled:
            return
        if not (0 <= fan_index < len(self.nbfc_parser.fans)):
            return
        fan = self.nbfc_parser.fans[fan_index]
        write_reg = fan['write_reg']
        self.fan_controller.set_last_speed(fan_index, speed)
        self.driver.write_register(write_reg, speed)

    def on_closing(self) -> None:
        if self.system_tray:
            self.main_window.withdraw()
        else:
            self.quit()

    def quit(self) -> None:
        self.stop_event.set()
        self.fan_controller.stop()
        self.plugin_manager.shutdown_plugins()
        if isinstance(self.default_sensor, WmiTempSensor):
            self.default_sensor.shutdown()

        # Shutdown detailed logging
        detailed_logger = get_detailed_logger()
        if detailed_logger:
            detailed_logger.shutdown()

        self.config._flush_changes()
        if self.system_tray and self.system_tray.icon:
            self.system_tray.icon.stop()
        self.main_window.quit()

    def run(self) -> None:
        if sys.platform == 'win32' and self.system_tray:
            threading.Thread(target=self.system_tray.create_icon, daemon=True).start()

        start_minimized = self.config.get("start_minimized", False) or '--start-in-tray' in sys.argv
        if start_minimized and sys.platform == 'win32':
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

import hashlib
from tkinter import messagebox

KNOWN_HASHES = {
    'inpoutx64.dll': '5f27ed4d5cd58a1ee23deeb802e09e73f3a1d884ce2135f6e827f67b171269e7',
    'LibreHardwareMonitorLib.dll': 'a0f2728f1734c236a9d02d9e25a88bc4f8cb7bd1faff1770726beb7af06bf8dc',
    'HidSharp.dll': '8c58e5fba22acc751032dfe97ce633e4f8a4c96089749bf316d55283b36649c2'
}

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

def verify_and_unblock(filepath: str) -> bool:
    """
    Verify DLL integrity and remove MOTW if valid.
    NOTE: Hash verification disabled pending manual hash generation.
    """
    filename = os.path.basename(filepath)
    logger = get_logger(__name__)

    if filename in KNOWN_HASHES and KNOWN_HASHES[filename] is not None:
        # Hash verification enabled
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        if file_hash != KNOWN_HASHES[filename]:
            logger.error(f"❌ Hash mismatch for {filename}! Possible tampering.")
            return False
    else:
        # Hash not set - log warning but proceed
        logger.warning(f"⚠️ Hash verification not configured for {filename}")

    # Unblock file
    unblock_file(filepath)
    return True


def main() -> None:
    setup_logger()
    if sys.platform == 'win32':
        myappid = 'vortecio.app.control.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        required_dlls = [
            'inpoutx64.dll',
            'plugins/lhm_sensor/LibreHardwareMonitorLib.dll',
            'plugins/lhm_sensor/HidSharp.dll'
        ]
        for dll_path in required_dlls:
            if not verify_and_unblock(dll_path):
                filename = os.path.basename(dll_path)
                logging.critical(f"Security violation: Hash mismatch for {filename}!")
                sys.exit(1)

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
