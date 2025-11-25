import json
import os

class AppConfig:
    def __init__(self, file_name="settings.json"):
        self.file_name = file_name
        self.defaults = {
            "last_config_path": None,
            "theme": "light",
            "language": "en",
            "autostart": False
        }
        self.config = self.defaults.copy()
        self.load()

    def load(self):
        if os.path.exists(self.file_name):
            try:
                with open(self.file_name, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge loaded config with defaults to ensure all keys are present
                    self.config.update(loaded_config)
            except (json.JSONDecodeError, TypeError):
                print("Error reading config file. Using defaults.")
                self.config = self.defaults.copy()
        else:
            print("Config file not found. Using defaults.")
            # If the file doesn't exist, we just use the defaults
            pass

    def save(self):
        try:
            with open(self.file_name, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config file: {e}")

    def get(self, key):
        return self.config.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save()
