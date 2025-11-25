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
            if self.app_logic.fan_control_disabled:
                self.stop_event.wait(3.0)
                continue

            sensor = self.app_logic.get_active_sensor()
            if not sensor:
                self.stop_event.wait(3.0)
                continue

            current_temp = sensor.get_temperature()

            if current_temp is None:
                self.sensor_errors += 1
                if self.sensor_errors * 3 >= 10:
                    self.trigger_panic_mode()
                    continue
            else:
                self.sensor_errors = 0
                # Update temperatures in the main UI
                self.app_logic.update_temperatures()

            for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
                slider_var = self.app_logic.main_window.fan_vars.get(f'fan_{i}_write')
                if not slider_var:
                    continue

                max_val = fan['max_speed']
                auto_val = max_val + 1

                if slider_var.get() == auto_val:
                    new_speed = self._get_speed_for_temp(i, fan, current_temp)
                    self.app_logic.set_fan_speed_internal(i, new_speed)

            self.stop_event.wait(3.0)

    def _get_speed_for_temp(self, fan_index, fan_config, temp):
        last_speed = self.last_speed.get(fan_index, 0)
        thresholds = sorted(fan_config['temp_thresholds'], key=lambda x: x[0])
        new_speed = last_speed

        if not thresholds:
            return last_speed  # No thresholds defined, maintain current speed

        # Determine if temperature is above the highest 'Up' threshold
        if temp > thresholds[-1][0]:
            new_speed = thresholds[-1][2]
        else:
            # Find the correct speed for the current temperature going up
            for up, down, speed in thresholds:
                if temp >= up and last_speed < speed:
                    new_speed = speed
                    break

        # Determine if temperature is below the lowest 'Down' threshold
        if temp < thresholds[0][1]:
            new_speed = thresholds[0][2]
        else:
            # Find the correct speed for the current temperature going down
            for up, down, speed in reversed(thresholds):
                if temp <= down and last_speed > speed:
                    new_speed = speed
                    break

        self.last_speed[fan_index] = new_speed
        return new_speed
