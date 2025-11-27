import json
import os
import threading
from logger import get_logger

class AppConfig:
    def __init__(self, file_name="settings.json"):
        self.logger = get_logger('Config')
        self.file_name = file_name
        self.defaults = {
            "last_config_path": None,
            "theme": "light",
            "language": "en",
            "autostart": False,
            "active_plugins": ["lhm_sensor"],
            "detailed_logging": False,
            "log_level": "INFO",
            "critical_temp_action": "ask",  # "ask", "disable", "continue", "ignore"
            "show_critical_warning": True,
            "prefer_lhm": True
        }
        self.config = self.defaults.copy()
        self._pending_changes = {}
        self._save_timer = None
        self._save_lock = threading.Lock()
        self.load()

    def load(self):
        if os.path.exists(self.file_name):
            try:
                with open(self.file_name, 'r') as f:
                    loaded_config = json.load(f)
                self.config.update(loaded_config)
                self.logger.info(f"Config loaded from {self.file_name}")
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.error(f"Error reading config: {e}")
                self.config = self.defaults.copy()
        else:
            self.logger.info("Config file not found, using defaults")

    def save(self):
        try:
            with open(self.file_name, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.debug("Config saved successfully")
        except IOError as e:
            self.logger.error(f"Error saving config: {e}")

    def get(self, key, default=None):
        with self._save_lock:
            if key in self.config:
                return self.config[key]
            if key in self.defaults:
                return self.defaults[key]
            return default

    def set(self, key, value):
        with self._save_lock:
            self.config[key] = value
            self._pending_changes[key] = value
            if self._save_timer:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(1.0, self._flush_changes)
            self._save_timer.start()
            self.logger.debug(f"Config queued: {key} = {value}")

    def _flush_changes(self):
        """Flush pending changes to disk"""
        with self._save_lock:
            # Cancel timer if exists
            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None

            if self._pending_changes:
                self.save()
                self.logger.info(f"Saved {len(self._pending_changes)} config changes")
                self._pending_changes.clear()
