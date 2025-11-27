import customtkinter as ctk
import os
from localization import translate
from ui.components import CTkMessageBox

class PluginManagerWindow(ctk.CTkToplevel):
    """Modern plugin manager window using customtkinter"""
    def __init__(self, parent, app_logic):
        super().__init__(parent)
        self.app_logic = app_logic

        self.title(translate('plugin_manager_title'))
        self.geometry("400x450")
        self.transient(parent)

        self.plugin_vars = {}
        self.initial_state = self.app_logic.config.get("active_plugins", [])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_widgets()

    def create_widgets(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(
            header,
            text=translate('select_active_plugins'),
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w")

        # Scrollable frame for plugin checkboxes
        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)

        plugin_folder = "plugins"
        available_plugins = []
        if os.path.exists(plugin_folder):
            for item in os.listdir(plugin_folder):
                item_path = os.path.join(plugin_folder, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                    available_plugins.append(item)

        for plugin_id in sorted(available_plugins):
            var = ctk.BooleanVar(value=(plugin_id in self.initial_state))
            checkbox = ctk.CTkCheckBox(scroll_frame, text=plugin_id, variable=var)
            checkbox.pack(anchor='w', padx=10, pady=5)
            self.plugin_vars[plugin_id] = var

        # Warning message
        ctk.CTkLabel(
            self,
            text=translate('plugins_restart_warning'),
            text_color="orange",
            font=ctk.CTkFont(size=12)
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=10)


        # Action buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            button_frame,
            text=translate('save'),
            command=self.save_and_close
        ).grid(row=0, column=0, sticky="ew", padx=5)

        ctk.CTkButton(
            button_frame,
            text=translate('cancel'),
            fg_color="gray",
            command=self.destroy
        ).grid(row=0, column=1, sticky="ew", padx=5)

    def save_and_close(self):
        """Save changes and show restart notification"""
        active_plugins = [name for name, var in self.plugin_vars.items() if var.get()]

        # Only show message if something actually changed
        if set(active_plugins) != set(self.initial_state):
            self.app_logic.config.set("active_plugins", active_plugins)
            CTkMessageBox(
                title=translate('restart_required_title'),
                message=translate('restart_required_msg'),
                icon="info"
            )
        self.destroy()
