import threading
import time
from tkinter import messagebox

class FanController:
    def __init__(self, app_logic):
        self.app_logic = app_logic
        self.stop_event = threading.Event()
        self.control_thread = None
        self.last_speed = {}
        self.sensor_errors = 0
        self.fan_states = {}  # Tracks the control state, e.g., 'active' or 'released'

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

    def trigger_panic_mode(self):
        if self.app_logic.fan_control_disabled:
            return
        self.app_logic.fan_control_disabled = True
        self.app_logic.main_window.after(0, lambda: messagebox.showerror("Sensor Error", "Thermal sensor failure. Fan control disabled for safety."))

    def control_loop(self):
        while not self.stop_event.is_set():
            parser = self.app_logic.nbfc_parser
            if not parser or not parser.fans:
                self.stop_event.wait(2.0)
                continue

            poll_interval_s = parser.ec_poll_interval / 1000.0
            all_fans_disabled = True

            # Sensor reading logic (only if not in deep sleep)
            current_temp = None
            should_poll_sensors = False
            for i, fan in enumerate(parser.fans):
                 slider_var = self.app_logic.main_window.fan_vars.get(f'fan_{i}_write')
                 if slider_var and slider_var.get() != (fan['min_speed'] - 2): # not disabled
                     should_poll_sensors = True
                     break

            if should_poll_sensors:
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

            for i, fan in enumerate(parser.fans):
                slider_var = self.app_logic.main_window.fan_vars.get(f'fan_{i}_write')
                if not slider_var:
                    continue

                fan_mode = slider_var.get()
                min_val, max_val = fan['min_speed'], fan['max_speed']
                disabled_val, read_only_val = min_val - 2, min_val - 1
                auto_val = max_val + 1

                is_active_control = fan_mode not in (disabled_val, read_only_val)

                if fan_mode != disabled_val:
                    all_fans_disabled = False

                if is_active_control:
                    # STATE: Active Control (Manual or Auto)
                    self.fan_states[i] = 'active'

                    speed_to_write = 0
                    if fan_mode == auto_val:
                        speed_to_write = self._get_speed_for_temp(i, fan, current_temp) if current_temp is not None else self.last_speed.get(i, 0)
                    else: # Manual
                        speed_to_write = fan_mode

                    self.app_logic.set_fan_speed_internal(i, speed_to_write)

                else:
                    # STATE: Passive Control (Disabled or Read-Only)
                    if self.fan_states.get(i) != 'released':
                        self.app_logic.set_fan_speed_internal(i, fan['reset_val'], force_write=True)
                        self.fan_states[i] = 'released'

            # Determine sleep duration
            if all_fans_disabled:
                self.stop_event.wait(2.0)  # Deep sleep
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
