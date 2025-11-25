import threading
import time
from tkinter import messagebox
from logger import get_logger

class FanController:
    def __init__(self, app_logic):
        self.app_logic = app_logic
        self.logger = get_logger('FanController')
        self.stop_event = threading.Event()
        self.control_thread = None
        self.last_speed = {}
        self.sensor_errors = 0
        self.logger.info("FanController initialized")

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
        """Головний цикл контролю вентиляторів"""
        self.logger.info("Fan control loop started")

        while not self.stop_event.is_set():
            if self.app_logic.fan_control_disabled:
                self.logger.warning("Fan control disabled, stopping loop")
                self.stop_event.wait(5.0)
                continue

            try:
                # Отримати температуру через LHM
                current_temp = self.app_logic.get_active_sensor().get_temperature()
                self.logger.debug(f"Current temperature: {current_temp}°C")

                # Оновити графік (thread-safe)
                self.app_logic.main_window.after(
                    0,
                    self.app_logic.main_window.temp_graph.add_temperature,
                    current_temp
                )

                # Контроль швидкості вентиляторів
                for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
                    slider_var = self.app_logic.main_window.fan_vars.get(f'fan_{i}_write')
                    if not slider_var:
                        continue

                    max_val = fan['max_speed']
                    auto_val = max_val + 1

                    if slider_var.get() == auto_val:
                        target_speed = self._get_speed_for_temp(i, fan, current_temp)

                        if target_speed != self.last_speed.get(i):
                            self.app_logic.set_fan_speed_internal(i, target_speed)
                            self.last_speed[i] = target_speed
                            self.logger.info(f"Fan {i} ({fan['name']}): {target_speed}% at {current_temp}°C")

                    # Читання RPM (опційно, через LHM якщо доступно)
                    if hasattr(self.app_logic.lhm_sensor, 'get_fan_rpm'):
                        rpm = self.app_logic.lhm_sensor.get_fan_rpm(i)
                        if rpm > 0:
                            self.logger.debug(f"Fan {i} RPM: {rpm}")

                # Reset error counter
                self.sensor_errors = 0

            except RuntimeError as e:
                # Критична помилка - сенсор відсутній
                self.logger.critical(f"Sensor error: {e}")
                self.trigger_panic_mode()
                break

            except Exception as e:
                self.sensor_errors += 1
                self.logger.error(f"Error in control loop: {e}", exc_info=True)

                if self.sensor_errors >= 5:
                    self.logger.critical("Too many sensor errors, triggering panic mode")
                    self.trigger_panic_mode()
                    break

            # Пауза між ітераціями
            self.stop_event.wait(2.0)

        self.logger.info("Fan control loop stopped")

    def _get_speed_for_temp(self, fan_index, fan_config, temp):
        last_speed = self.last_speed.get(fan_index, 0)
        thresholds = sorted(fan_config['temp_thresholds'], key=lambda x: x[0])
        new_speed = last_speed

        if temp > (thresholds[-1][0] if thresholds else 100):
            new_speed = thresholds[-1][2]
        else:
            for up, down, speed in thresholds:
                if temp >= up and last_speed < speed:
                    new_speed = speed
                    break

        if temp < (thresholds[0][1] if thresholds else 0):
            new_speed = thresholds[0][2]
        else:
            for up, down, speed in reversed(thresholds):
                if temp <= down and last_speed > speed:
                    new_speed = speed
                    break

        self.last_speed[fan_index] = new_speed
        return new_speed
