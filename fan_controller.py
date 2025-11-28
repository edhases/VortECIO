import threading
import time
import bisect
from typing import Dict, Any, Optional
from logger import get_logger
from utils import normalize_fan_speed, denormalize_fan_speed
from advanced_logging import get_detailed_logger


logger = get_logger(__name__)

class FanController:
    def __init__(self, app_logic: 'AppLogic') -> None:
        self.app_logic: 'AppLogic' = app_logic
        self.logger = get_logger(__name__)
        self.stop_event: threading.Event = threading.Event()
        self.control_thread: Optional[threading.Thread] = None
        self.last_speed: Dict[int, int] = {}
        self.sensor_errors: int = 0
        self.fan_states: Dict[int, str] = {}
        self.critical_temperature: float = 90.0
        self.max_observed_speed: Dict[int, int] = {}
        self._fan_mode_cache: Dict[int, int] = {}
        self._cache_lock: threading.Lock = threading.Lock()
        self._cache_updated: threading.Event = threading.Event()
        self.last_cpu_temp = None
        self.last_gpu_temp = None

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

    def trigger_panic_mode(self):
        """Handle critical temperature - simplified approach."""
        if self.app_logic.fan_control_disabled:
            return

        action = self.app_logic.config.get("critical_temp_action", "ask")

        if action == "ask":
            # Show informational dialog (first time)
            self.show_critical_info_dialog()
            # Set to 'disable' so we don't spam dialogs
            self.app_logic.config.set("critical_temp_action", "disable")
            self.app_logic.fan_control_disabled = True
        elif action == "disable":
            # Disable silently
            self.app_logic.fan_control_disabled = True
        elif action == "continue":
            # Log warning but continue
            self.logger.warning(f"Critical temp {self.last_cpu_temp}°C - continuing per user config")
        # "ignore" - do nothing

    def show_critical_info_dialog(self):
        """Show informational dialog about panic mode."""
        def show():
            from ui.main_window import CTkMessageBox

            current_temp = getattr(self, 'last_cpu_temp', 0) or getattr(self, 'last_gpu_temp', 0) or 0

            CTkMessageBox(
                title="⚠️ Critical Temperature",
                message=(
                    f"Critical temperature detected: {current_temp:.1f}°C\n"
                    f"Threshold: {self.critical_temperature:.1f}°C\n\n"
                    f"Fan control has been DISABLED for safety.\n"
                    f"BIOS will now manage your fans.\n\n"
                    f"You can change this behavior in:\n"
                    f"Settings → Advanced → Critical Temperature Behavior\n\n"
                    f"Restart the app after temperatures normalize."
                ),
                icon="warning"
            )

        self.app_logic.main_window.after(0, show)

    def _update_fan_mode_cache(self) -> None:
        with self._cache_lock:
            try:
                if not self.app_logic.nbfc_parser:
                    return
                for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
                    auto_val = fan['max_speed'] + 1
                    # Read from new UI structure
                    mode_str_var = self.app_logic.main_window.fan_mode_vars.get(i)
                    if mode_str_var:
                        mode_value = mode_str_var.get()

                        # Mode mapping: string -> internal integer
                        mode_mapping = {
                            'Auto': auto_val,
                            'Read-only': fan['min_speed'] - 1,
                            'Disabled': fan['min_speed'] - 2,
                            'Manual': None  # Special: read from slider
                        }

                        if mode_value == 'Manual':
                            # For manual mode, read slider value
                            slider_var = self.app_logic.main_window.fan_slider_vars.get(i)
                            if slider_var:
                                self._fan_mode_cache[i] = slider_var.get()
                            else:
                                self._fan_mode_cache[i] = 50  # Default 50%
                        else:
                            self._fan_mode_cache[i] = mode_mapping.get(mode_value, auto_val)
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
                    self.last_cpu_temp = cpu_temp
                    self.last_gpu_temp = gpu_temp
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

                    detailed_logger = get_detailed_logger()
                    if detailed_logger:
                        sensor_type = 'LHM' if self.app_logic.plugin_sensor else 'WMI'
                        detailed_logger.log_sensor_read(
                            sensor_type=sensor_type,
                            cpu_temp=cpu_temp,
                            gpu_temp=gpu_temp,
                            success=(current_temp is not None)
                        )

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
                            # Auto mode: calculate from temperature
                            speed_percent = self._get_speed_for_temp(i, fan, current_temp) if current_temp is not None else self.last_speed.get(i, 0)
                            speed_to_write = denormalize_fan_speed(speed_percent, fan)
                        elif fan_mode == read_only_val or fan_mode == disabled_val:
                            # These modes are handled by the is_active_control check, but we continue defensively.
                            continue
                        else:
                            # Manual mode: Assume it's a percentage from the new UI
                            speed_to_write = denormalize_fan_speed(fan_mode, fan)
                        self.app_logic.set_fan_speed_internal(i, speed_to_write)
                    else:
                        if self.fan_states.get(i) != 'released':
                            self.app_logic.set_fan_speed_internal(i, fan['reset_val'], force_write=True)
                            self.fan_states[i] = 'released'

                    if fan_mode == disabled_val:
                        # In disabled mode, clear the UI and do nothing else
                        if self.fan_states.get(i) != 'released':
                            self.app_logic.main_window.after(0, self.app_logic.main_window.clear_fan_display, i)
                    else:
                        # For all other modes (Auto, Manual, Read-only), read and display RPM
                        rpm = self.app_logic.driver.read_register(fan['read_reg'])
                        if rpm is not None:
                            percent = self._calculate_percent(i, rpm, fan)
                            self.app_logic.main_window.after(0, self.app_logic.main_window.update_fan_readings, i, rpm, percent)
                            detailed_logger = get_detailed_logger()
                            if detailed_logger:
                                detailed_logger.log_fan_state(
                                    fan_index=i,
                                    temp=current_temp,
                                    speed=percent,
                                    rpm=rpm,
                                    mode=self._get_mode_name(fan_mode, min_val, max_val)
                                )

            loop_duration = time.perf_counter() - loop_start
            loop_count += 1
            if loop_duration > poll_interval_s * 1.5:
                slow_loops += 1
                logger.warning(f"Slow control loop: {loop_duration:.3f}s (target: {poll_interval_s:.3f}s)")

            detailed_logger = get_detailed_logger()
            if detailed_logger:
                detailed_logger.log_performance('control_loop', loop_duration * 1000)

            if loop_count % 100 == 0:
                if slow_loops > 0:
                    logger.info(f"Control loop stats: {loop_count} iterations, {slow_loops} slow ({slow_loops/loop_count*100:.1f}%)")
                slow_loops = 0

            sleep_duration = max(0.01, poll_interval_s - loop_duration)
            self.stop_event.wait(sleep_duration)

    def _get_mode_name(self, fan_mode: int, min_val: int, max_val: int) -> str:
        """Convert fan_mode int to readable name"""
        disabled_val = min_val - 2
        read_only_val = min_val - 1
        auto_val = max_val + 1

        if fan_mode == disabled_val:
            return 'disabled'
        elif fan_mode == read_only_val:
            return 'read_only'
        elif fan_mode == auto_val:
            return 'auto'
        else:
            return 'manual'

    def _calculate_percent(self, fan_index: int, rpm: int, fan_config: Dict[str, Any]) -> int:
        # Priority 1: Use independent read values if specified in config (NBFC standard)
        if fan_config.get('independent_read_min_max', False):
            min_read = fan_config.get('min_speed_read', 0)
            max_read = fan_config.get('max_speed_read', 0)
            return normalize_fan_speed(rpm, fan_config, min_val=min_read, max_val=max_read)

        # Priority 2: Use adaptive RPM scaling
        config_max = fan_config.get('max_speed', 255)

        # If RPM looks like a raw RPM value (significantly higher than 255)
        if rpm > config_max * 1.5:
            # --- COLD START FIX ---
            # Initialize max_observed_speed with the first valid reading > 0.
            # This prevents the "66%" issue by treating the current speed as 100% initially.
            if fan_index not in self.max_observed_speed and rpm > 0:
                self.max_observed_speed[fan_index] = rpm
            # ----------------------

            max_observed = self.max_observed_speed.get(fan_index, 3000)

            # Update max_observed only if the new value is realistic (filter glitches > 12000)
            if rpm > max_observed and rpm < 12000:
                self.max_observed_speed[fan_index] = rpm
                max_observed = rpm

            if max_observed == 0:
                return 0

            percent = int((rpm / max_observed) * 100)
            return min(100, max(0, percent))

        # Fallback: Standard normalization
        return normalize_fan_speed(rpm, fan_config)

    def _get_speed_for_temp(self, fan_index: int, fan_config: Dict[str, Any], temp: Optional[float]) -> int:
        last_speed = self.last_speed.get(fan_index, 0)
        thresholds = fan_config.get('temp_thresholds', [])

        if not thresholds or temp is None:
            return last_speed

        # Binary search for target zone
        up_temps = [t[0] for t in thresholds]
        idx = bisect.bisect_right(up_temps, temp)

        if idx == 0:
            target_speed = 0
        else:
            target_speed = thresholds[idx - 1][2]

        # Apply hysteresis
        new_speed = last_speed

        if target_speed > last_speed:
            # Temperature rising: switch immediately
            new_speed = target_speed
        elif target_speed < last_speed:
            # Temperature falling: check down threshold
            current_zone_idx = None

            # Try to find zone matching last_speed
            for i, (up, down, speed) in enumerate(thresholds):
                if speed == last_speed:
                    current_zone_idx = i
                    break

            if current_zone_idx is not None:
                # Normal case: last_speed matches a threshold
                down_threshold = thresholds[current_zone_idx][1]
                if temp <= down_threshold:
                    new_speed = target_speed
            else:
                # FALLBACK: last_speed is non-standard (manual override)
                # Use target zone's down threshold for hysteresis
                if idx > 0:
                    # We're in a defined zone - use its down threshold
                    fallback_down = thresholds[idx - 1][1]
                    if temp <= fallback_down:
                        new_speed = target_speed
                        self.logger.debug(f"Fan {fan_index}: Non-standard speed {last_speed}%, "
                                         f"using fallback hysteresis (down={fallback_down}°C)")
                else:
                    # Below all thresholds - drop to minimum immediately
                    new_speed = target_speed

        self.last_speed[fan_index] = new_speed
        return new_speed

    def set_fan_mode_cached(self, fan_index: int, mode_value: int) -> None:
        """
        Update cached fan mode (thread-safe).
        Called from UI thread when user changes mode dropdown.
        """
        with self._cache_lock:
            self._fan_mode_cache[fan_index] = mode_value

    def set_last_speed(self, fan_index: int, speed: int) -> None:
        self.last_speed[fan_index] = speed
