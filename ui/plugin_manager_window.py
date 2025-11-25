import tkinter as tk
from tkinter import ttk, messagebox
import os

class PluginManagerWindow(tk.Toplevel):
    def __init__(self, parent, app_logic):
        super().__init__(parent)
        self.app_logic = app_logic
        self.title("Manage Plugins")
        self.geometry("300x400")

        self.plugin_vars = {}
        self.changed = False

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill='both')

        label = ttk.Label(main_frame, text="Select active plugins:")
        label.pack(anchor='w', pady=(0, 10))

        plugin_folder = "plugins"
        if os.path.exists(plugin_folder):
            for item in os.listdir(plugin_folder):
                item_path = os.path.join(plugin_folder, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                    var = tk.BooleanVar()
                    var.set(item in self.app_logic.config.get("active_plugins", []))
                    cb = ttk.Checkbutton(main_frame, text=item, variable=var, command=self.on_change)
                    cb.pack(anchor='w')
                    self.plugin_vars[item] = var

    def on_change(self):
        self.changed = True

    def on_closing(self):
        if self.changed:
            active_plugins = [name for name, var in self.plugin_vars.items() if var.get()]
            self.app_logic.config.set("active_plugins", active_plugins)
            messagebox.showinfo("Restart Required", "Please restart the application to apply plugin changes.")
        self.destroy()
