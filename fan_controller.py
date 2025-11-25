import threading
import time

class FanController:
    def __init__(self, app_logic): # Прибираємо temp_sensor з __init__
        self.app_logic = app_logic
        # Сенсор тепер беремо з app_logic (який може бути оновлений плагінами)
        self.stop_event = threading.Event()
        self.control_thread = None
        self.last_speed = {}

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

    def control_loop(self):
        while not self.stop_event.is_set():
            # Динамічно отримуємо поточний сенсор
            sensor = self.app_logic.get_active_sensor()
            if not sensor:
                self.stop_event.wait(3.0)
                continue
            current_temp = sensor.get_temperature()

            for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
                slider_var = self.app_logic.main_window.fan_vars.get(f'fan_{i}_write')
                if not slider_var:
                    continue

                min_val = fan['min_speed']
                max_val = fan['max_speed']
                disabled_val = min_val - 2
                read_only_val = min_val - 1
                auto_val = max_val + 1

                # Check if this fan is in automatic mode
                if slider_var.get() == auto_val:
                    new_speed = self._get_speed_for_temp(i, fan, current_temp)

                    # Update the fan speed via the main app logic
                    # No need to set slider_var here as it is already "Auto"
                    self.app_logic.set_fan_speed_internal(i, new_speed)
                elif slider_var.get() in (read_only_val, disabled_val):
                    # Do nothing
                    pass

            self.stop_event.wait(3.0) # Збільш інтервал до 3 сек для WMI

    def _get_speed_for_temp(self, fan_index, fan_config, temp):
        last_speed = self.last_speed.get(fan_index, 0)

        # Sort thresholds by the 'up' value
        thresholds = sorted(fan_config['temp_thresholds'], key=lambda x: x[0])

        new_speed = last_speed

        # If temperature is rising
        if temp > (thresholds[-1][0] if thresholds else 100): # If above highest up-threshold
             new_speed = thresholds[-1][2]
        else:
            for up, down, speed in thresholds:
                if temp >= up and last_speed < speed:
                    new_speed = speed
                    break

        # If temperature is falling
        if temp < (thresholds[0][1] if thresholds else 0): # If below lowest down-threshold
            new_speed = thresholds[0][2]
        else:
            for up, down, speed in reversed(thresholds):
                 if temp <= down and last_speed > speed:
                    new_speed = speed
                    break

        self.last_speed[fan_index] = new_speed
        return new_speed
