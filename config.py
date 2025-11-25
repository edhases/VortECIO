import json
import os
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
            "active_plugins": ["lhm_sensor"]  # LHM за замовчуванням!
        }
        self.config = self.defaults.copy()
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
        if key in self.config:
            return self.config[key]
        if key in self.defaults:
            return self.defaults[key]
        return default

    def set(self, key, value):
        self.config[key] = value
        self.save()
        self.logger.debug(f"Config updated: {key} = {value}")
