import os
import importlib.util

class PluginManager:
    def __init__(self, app_logic, plugin_folder="plugins"):
        self.app_logic = app_logic
        self.plugin_folder = plugin_folder
        self.plugins = []

    def discover_plugins(self):
        if not os.path.exists(self.plugin_folder):
            return

        for item in os.listdir(self.plugin_folder):
            item_path = os.path.join(self.plugin_folder, item)
            if os.path.isdir(item_path):
                # This could be a plugin package
                self.load_plugin_package(item_path)

    def load_plugin_package(self, path):
        # Look for an __init__.py to signify a package
        init_file = os.path.join(path, "__init__.py")
        if not os.path.exists(init_file):
            return

        package_name = os.path.basename(path)

        try:
            # Dynamically load the plugin's __init__.py as a module
            spec = importlib.util.spec_from_file_location(package_name, init_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check if the plugin has a 'register' function
            if hasattr(module, 'register'):
                plugin_instance = module.register(self.app_logic)
                if plugin_instance:
                    self.plugins.append(plugin_instance)
                    print(f"Loaded plugin: {package_name}")

        except ImportError as e:
            print(f"Failed to load plugin {package_name}: {e}")

    def initialize_plugins(self):
        for plugin in self.plugins:
            if hasattr(plugin, 'initialize'):
                plugin.initialize()

    def shutdown_plugins(self):
        for plugin in self.plugins:
            if hasattr(plugin, 'shutdown'):
                plugin.shutdown()
