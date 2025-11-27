import customtkinter as ctk
from localization import translate

class PluginManagerWindow(ctk.CTkToplevel):
    """Plugin management window using CustomTkinter."""

    def __init__(self, parent, app_logic):
        super().__init__(parent)

        self.app_logic = app_logic

        # Use translate() for consistency
        self.title(translate('plugin_manager_title'))
        self.geometry("500x400")

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Header
        header = ctk.CTkLabel(
            self,
            text=translate('select_active_plugins'),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header.pack(pady=20, padx=20, anchor="w")

        # Scrollable frame for checkboxes
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=460, height=250)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Get available plugins
        available_plugins = self.app_logic.plugin_manager.available_plugins
        active_plugins = self.app_logic.config.get('active_plugins', [])

        self.plugin_vars = {}

        for plugin_id in available_plugins:
            var = ctk.BooleanVar(value=(plugin_id in active_plugins))
            self.plugin_vars[plugin_id] = var

            # Plugin info
            plugin_name = plugin_id.replace('_', ' ').title()

            checkbox = ctk.CTkCheckBox(
                self.scroll_frame,
                text=plugin_name,
                variable=var,
                font=ctk.CTkFont(size=14)
            )
            checkbox.pack(pady=5, padx=10, anchor="w")

        # Buttons frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20, padx=20, fill="x")

        # Save button
        save_btn = ctk.CTkButton(
            button_frame,
            text=translate('save'),
            command=self.save_and_close,
            width=120
        )
        save_btn.pack(side="left", padx=5)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            button_frame,
            text=translate('cancel'),
            command=self.destroy,
            width=120,
            fg_color="gray"
        )
        cancel_btn.pack(side="left", padx=5)

        # Info label
        info = ctk.CTkLabel(
            self,
            text=translate('plugins_restart_warning'),
            text_color="orange",
            font=ctk.CTkFont(size=10)
        )
        info.pack(pady=5)

    def save_and_close(self):
        """Save selected plugins to config."""
        active_plugins = [
            plugin_id for plugin_id, var in self.plugin_vars.items()
            if var.get()
        ]

        self.app_logic.config.set('active_plugins', active_plugins)
        self.destroy()
