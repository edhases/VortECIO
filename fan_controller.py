import threading
import time
import bisect
from tkinter import messagebox
from typing import Dict, Any, Optional
from logger import get_logger
from utils import normalize_fan_speed, denormalize_fan_speed


logger = get_logger(__name__)

class FanController:
    def __init__(self, app_logic: 'AppLogic') -> None:
        self.app_logic: 'AppLogic' = app_logic
        self.stop_event: threading.Event = threading.Event()
        self.control_thread: Optional[threading.Thread] = None
        self.last_speed: Dict[int, int] = {}
        self.sensor_errors: int = 0
        self.fan_states: Dict[int, str] = {}
        self.critical_temperature: float = 90.0
        self._fan_mode_cache: Dict[int, int] = {}
        self._cache_lock: threading.Lock = threading.Lock()
        self._cache_updated: threading.Event = threading.Event()

    def start(self) -> None:
        if self.control_thread and self.control_thread.is_alive():
            return
        self.stop_event.clear()
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)

    def trigger_panic_mode(self) -> None:
        if self.app_logic.fan_control_disabled:
            return
        self.app_logic.fan_control_disabled = True
        self.sensor_errors = 0
        self.app_logic.main_window.after(0, lambda: messagebox.showerror("Sensor Error", "Thermal sensor failure. Fan control disabled for safety."))

    def _update_fan_mode_cache(self) -> None:
        with self._cache_lock:
            try:
                if not self.app_logic.nbfc_parser:
                    return
                for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
                    auto_val = fan['max_speed'] + 1
                    slider_var = self.app_logic.main_window.fan_vars.get(f'fan_{i}_write')
                    if slider_var:
                        self._fan_mode_cache[i] = slider_var.get()
                    else:
                        self._fan_mode_cache[i] = auto_val
            except Exception as e:
                logger.error(f"Error updating fan mode cache: {e}")
            finally:
                self._cache_updated.set()

    def control_loop(self) -> None:
        loop_count = 0
        slow_loops = 0

        while not self.stop_event.is_set():
            loop_start = time.perf_counter()

            parser = self.app_logic.nbfc_parser
            if not parser or not parser.fans:
                self.stop_event.wait(2.0)
                continue

            self._cache_updated.clear()
            self.app_logic.main_window.after(0, self._update_fan_mode_cache)
            cache_updated = self._cache_updated.wait(timeout=0.1)
            if not cache_updated:
                logger.warning("Timed out waiting for UI fan mode cache update; using stale data.")

            poll_interval_s = parser.ec_poll_interval / 1000.0
            all_fans_disabled = True
            current_temp = None
            should_poll_sensors = False

            with self._cache_lock:
                for i, fan in enumerate(parser.fans):
                    fan_mode = self._fan_mode_cache.get(i)
                    if fan_mode is not None and fan_mode != (fan['min_speed'] - 2):
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
                        if current_temp >= self.critical_temperature:
                            logger.critical(f"CRITICAL TEMP: {current_temp}°C >= {self.critical_temperature}°C")
                            self.trigger_panic_mode()
                            continue
                        self.sensor_errors = 0
                    else:
                        self.sensor_errors += 1
                        if self.sensor_errors >= 10:
                            self.trigger_panic_mode()
                            self.sensor_errors = 0
                            continue

            with self._cache_lock:
                for i, fan in enumerate(parser.fans):
                    min_val, max_val = fan['min_speed'], fan['max_speed']
                    disabled_val, read_only_val = min_val - 2, min_val - 1
                    auto_val = max_val + 1
                    fan_mode = self._fan_mode_cache.get(i, auto_val)
                    is_active_control = fan_mode not in (disabled_val, read_only_val)
                    if fan_mode != disabled_val:
                        all_fans_disabled = False

                    if is_active_control:
                        self.fan_states[i] = 'active'
                        speed_to_write = 0
                        if fan_mode == auto_val:
                            hysteresis_start = time.perf_counter()
                            speed_percent = self._get_speed_for_temp(i, fan, current_temp) if current_temp is not None else self.last_speed.get(i, 0)
                            hysteresis_time = time.perf_counter() - hysteresis_start
                            if hysteresis_time > 0.001:
                                logger.debug(f"Hysteresis calculation took {hysteresis_time*1000:.2f}ms for fan {i}")
                            speed_to_write = denormalize_fan_speed(speed_percent, fan)
                        else:
                            speed_to_write = denormalize_fan_speed(fan_mode, fan)
                        self.app_logic.set_fan_speed_internal(i, speed_to_write)
                    else:
                        if self.fan_states.get(i) != 'released':
                            self.app_logic.set_fan_speed_internal(i, fan['reset_val'], force_write=True)
                            self.fan_states[i] = 'released'

                    if fan_mode != disabled_val:
                        rpm = self.app_logic.driver.read_register(fan['read_reg'])
                        if rpm is not None:
                            percent = self._calculate_percent(rpm, fan)
                            self.app_logic.main_window.after(0, self.app_logic.main_window.update_fan_readings, i, rpm, percent)

            loop_duration = time.perf_counter() - loop_start
            loop_count += 1
            if loop_duration > poll_interval_s * 1.5:
                slow_loops += 1
                logger.warning(f"Slow control loop: {loop_duration:.3f}s (target: {poll_interval_s:.3f}s)")

            if loop_count % 100 == 0:
                if slow_loops > 0:
                    logger.info(f"Control loop stats: {loop_count} iterations, {slow_loops} slow ({slow_loops/loop_count*100:.1f}%)")
                slow_loops = 0

            sleep_duration = max(0.01, poll_interval_s - loop_duration)
            self.stop_event.wait(sleep_duration)

    def _calculate_percent(self, rpm: int, fan_config: Dict[str, Any]) -> int:
        return normalize_fan_speed(rpm, fan_config)

    def _get_speed_for_temp(self, fan_index: int, fan_config: Dict[str, Any], temp: Optional[float]) -> int:
        """
        Determine fan speed based on temperature with hysteresis.
        Uses binary search for O(log n) performance.
        Args:
            fan_index: Index of the fan
            fan_config: Fan configuration dict with 'temp_thresholds' key
            temp: Current temperature in Celsius

        Returns:
            Target fan speed (percentage, 0-100)
        """
        last_speed = self.last_speed.get(fan_index, 0)
        thresholds = fan_config.get('temp_thresholds', [])

        if not thresholds or temp is None:
            return last_speed

        # Thresholds are already sorted in main.py
        # Format: [(up_temp, down_temp, speed), ...]

        # Binary search for the appropriate threshold
        up_temps = [t[0] for t in thresholds]
        idx = bisect.bisect_right(up_temps, temp)

        # Determine target speed zone
        if idx == 0:
            # Below all thresholds
            target_speed = 0
        else:
            # At or above threshold idx-1
            target_speed = thresholds[idx - 1][2]

        # Apply hysteresis
        new_speed = last_speed

        if target_speed > last_speed:
            # Temperature rising: switch immediately
            new_speed = target_speed
        elif target_speed < last_speed:
            # Temperature falling: check down threshold
            # Find current speed zone
            current_zone_idx = None
            for i, (up, down, speed) in enumerate(thresholds):
                if speed == last_speed:
                    current_zone_idx = i
                    break

            if current_zone_idx is not None:
                down_threshold = thresholds[current_zone_idx][1]
                if temp <= down_threshold:
                    # Below down threshold: allow speed decrease
                    new_speed = target_speed
                # else: stay in hysteresis zone (new_speed = last_speed)

        self.last_speed[fan_index] = new_speed
        return new_speed

    def set_last_speed(self, fan_index: int, speed: int) -> None:
        self.last_speed[fan_index] = speed
