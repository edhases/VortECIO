import os
import importlib.util
from logger import get_logger

class PluginManager:
    def __init__(self, app_logic, plugin_folder="plugins"):
        self.app_logic = app_logic
        self.plugin_folder = plugin_folder
        self.plugins = []
        self.active_plugins = self.app_logic.config.get("active_plugins", [])

    def discover_plugins(self):
        """Пошук та завантаження плагінів"""
        if not os.path.exists(self.plugin_folder):
            self.logger.warning(f"Plugin folder not found: {self.plugin_folder}")
            return

        self.logger.info("Discovering plugins...")

        for item in os.listdir(self.plugin_folder):
            item_path = os.path.join(self.plugin_folder, item)
            if os.path.isdir(item_path):
                if item in self.active_plugins:
                    self.load_plugin_package(item_path)

    def load_plugin_package(self, path):
        init_file = os.path.join(path, "__init__.py")
        if not os.path.exists(init_file):
            self.logger.warning(f"Plugin __init__.py not found: {path}")
            return

        package_name = os.path.basename(path)

        try:
            spec = importlib.util.spec_from_file_location(package_name, init_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, 'register'):
                self.logger.info(f"Registering plugin: {package_name}")
                plugin_instance = module.register(self.app_logic)

                if plugin_instance:
                    self.plugins.append(plugin_instance)
                    self.logger.info(f"Plugin {package_name} loaded successfully")
                else:
                    self.logger.error(f"Plugin {package_name} registration failed")
            else:
                self.logger.error(f"Plugin {package_name} has no register() function")

        except Exception as e:
            self.logger.error(f"Failed to load plugin {package_name}: {e}", exc_info=True)

    def initialize_plugins(self):
        for plugin in self.plugins:
            if hasattr(plugin, 'initialize'):
                plugin.initialize()

    def shutdown_plugins(self):
        for plugin in self.plugins:
            if hasattr(plugin, 'shutdown'):
                plugin.shutdown()
