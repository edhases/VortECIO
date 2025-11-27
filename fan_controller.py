import threading
import time
from logger import get_logger

logger = get_logger(__name__)

class FanController:
    def __init__(self, app_logic):
        self.app_logic = app_logic
        self.stop_event = threading.Event()
        self.control_thread = None
        self.last_speed = {}
        self.sensor_errors = 0
        self.fan_states = {}  # Tracks the control state, e.g., 'active' or 'released'
        self._fan_mode_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_updated = threading.Event()

    def _update_fan_mode_cache(self) -> None:
        with self._cache_lock:
            try:
                if not self.app_logic.nbfc_parser:
                    return

                for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
                    auto_val = fan['max_speed'] + 1

                    # Read from new UI structure (fan_mode_vars)
                    mode_var = self.app_logic.main_window.fan_mode_vars.get(i)
                    if mode_var:
                        mode_str = mode_var.get()  # "Auto", "Manual", "Read-only", "Disabled"

                        # Convert mode name to internal value
                        mode_mapping = {
                            'Auto': fan['max_speed'] + 1,
                            'Manual': -1,  # Special flag - use slider value
                            'Read-only': fan['min_speed'] - 1,
                            'Disabled': fan['min_speed'] - 2
                        }

                        internal_mode = mode_mapping.get(mode_str, auto_val)

                        # For Manual mode, read slider value
                        if mode_str == 'Manual':
                            slider_var = self.app_logic.main_window.fan_slider_vars.get(i)
                            if slider_var:
                                # Slider is in percentage (0-100), store as-is
                                self._fan_mode_cache[i] = int(slider_var.get())
                            else:
                                self._fan_mode_cache[i] = 50  # Default 50%
                        else:
                            self._fan_mode_cache[i] = internal_mode
                    else:
                        self._fan_mode_cache[i] = auto_val
            except Exception as e:
                logger.error(f"Error updating fan mode cache: {e}")
            finally:
                self._cache_updated.set()

    def start(self):
        if self.control_thread and self.control_thread.is_alive():
            return
        self.stop_event.clear()
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)

    def trigger_panic_mode(self) -> None:
        if self.app_logic.fan_control_disabled:
            return

        self.app_logic.fan_control_disabled = True
        self.sensor_errors = 0

        # Use customtkinter messagebox instead of tkinter
        def show_error():
            from ui.main_window import CTkMessageBox
            CTkMessageBox(
                title="Sensor Error",
                message="Thermal sensor failure. Fan control disabled for safety.",
                icon="warning"
            )

        self.app_logic.main_window.after(0, show_error)

    def control_loop(self):
        while not self.stop_event.is_set():
            parser = self.app_logic.nbfc_parser
            if not parser or not parser.fans:
                self.stop_event.wait(2.0)
                continue

            # --- Start of new logic ---
            self._cache_updated.clear()
            self.app_logic.main_window.after(0, self._update_fan_mode_cache)
            self._cache_updated.wait(timeout=1.0) # Wait for UI thread to update cache

            poll_interval_s = parser.ec_poll_interval / 1000.0
            all_fans_disabled = True
            current_temp = None

            with self._cache_lock:
                # Determine if we need to poll sensors
                should_poll_sensors = any(
                    self._fan_mode_cache.get(i, fan['min_speed'] - 2) != (fan['min_speed'] - 2)
                    for i, fan in enumerate(parser.fans)
                )

                if not should_poll_sensors:
                    self.stop_event.wait(2.0) # Deep sleep if all fans are disabled
                    continue

                # Sensor reading logic
                sensor = self.app_logic.get_active_sensor()
                if sensor:
                    cpu_temp, gpu_temp = sensor.get_temperatures()
                    self.app_logic.main_window.after(0, self.app_logic.main_window.update_temp_readings, cpu_temp, gpu_temp)
                    temps = [t for t in (cpu_temp, gpu_temp) if t is not None]
                    if temps:
                        current_temp = max(temps)
                        self.sensor_errors = 0
                    else:
                        self.sensor_errors += 1
                        if self.sensor_errors * poll_interval_s >= 10:
                            self.trigger_panic_mode()
                            continue

                # Fan control logic based on cache
                for i, fan in enumerate(parser.fans):
                    fan_mode = self._fan_mode_cache.get(i)
                    if fan_mode is None:
                        continue

                    min_val, max_val = fan['min_speed'], fan['max_speed']
                    disabled_val, read_only_val = min_val - 2, min_val - 1
                    auto_val = max_val + 1

                    is_active_control = fan_mode not in (disabled_val, read_only_val)

                    if fan_mode != disabled_val:
                        all_fans_disabled = False

                    if is_active_control:
                        self.fan_states[i] = 'active'
                        speed_to_write = 0
                        if fan_mode == auto_val: # Auto mode
                            speed_to_write = self._get_speed_for_temp(i, fan, current_temp) if current_temp is not None else self.last_speed.get(i, 0)
                        else: # Manual mode (fan_mode is the percentage)
                            speed_to_write = int((fan_mode / 100) * max_val)

                        self.app_logic.set_fan_speed_internal(i, speed_to_write)
                    else:
                        if self.fan_states.get(i) != 'released':
                            self.app_logic.set_fan_speed_internal(i, fan['reset_val'], force_write=True)
                            self.fan_states[i] = 'released'

            # Determine sleep duration outside the lock
            if all_fans_disabled:
                 self.stop_event.wait(2.0)
            else:
                 self.stop_event.wait(poll_interval_s)

    def _get_speed_for_temp(self, fan_index, fan_config, temp):
        last_speed = self.last_speed.get(fan_index, 0)
        thresholds = sorted(fan_config['temp_thresholds'], key=lambda x: x[0])
        new_speed = last_speed

        if not thresholds:
            return last_speed

        if temp > thresholds[-1][0]:
            new_speed = thresholds[-1][2]
        else:
            for up, down, speed in thresholds:
                if temp >= up and last_speed < speed:
                    new_speed = speed
                    break

        if temp < thresholds[0][1]:
            new_speed = thresholds[0][2]
        else:
            for up, down, speed in reversed(thresholds):
                if temp <= down and last_speed > speed:
                    new_speed = speed
                    break

        self.last_speed[fan_index] = new_speed
        return new_speed

    def set_last_speed(self, fan_index, speed):
        self.last_speed[fan_index] = speed
