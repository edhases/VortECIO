import customtkinter as ctk
import webbrowser
from CTkToolTip import CTkToolTip
from ui.main_window import CTkMessageBox
import os

class SettingsWindow(ctk.CTkToplevel):
    """Separate settings window - keeps main window clean"""

    def __init__(self, parent, app_logic):
        super().__init__(parent)
        self.app_logic = app_logic

        self.title("Settings")
        self.geometry("500x600")
        self.transient(parent)  # Modal

        # Tabview for organized settings
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # Tabs
        tabview.add("General")
        tabview.add("Appearance")
        tabview.add("Advanced")
        tabview.add("About")

        self.create_general_tab(tabview.tab("General"))
        self.create_appearance_tab(tabview.tab("Appearance"))
        self.create_advanced_tab(tabview.tab("Advanced"))
        self.create_about_tab(tabview.tab("About"))

    def create_general_tab(self, parent):
        """General settings"""
        # Load config
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text="Configuration",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)

        ctk.CTkButton(
            frame,
            text="📂 Load Config File",
            command=self.app_logic.load_config_file
        ).pack(fill="x", pady=5)

        # Current config display
        current_label = ctk.CTkLabel(
            frame,
            text=f"Current: {self.app_logic.nbfc_parser.model_name}",
            text_color="gray"
        )
        current_label.pack(anchor="w", pady=5)

        # Autostart
        startup_frame = ctk.CTkFrame(parent)
        startup_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(startup_frame, text="Startup",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)

        autostart_var = ctk.BooleanVar(value=self.app_logic.config.get("autostart"))
        ctk.CTkCheckBox(
            startup_frame,
            text="Start with Windows",
            variable=autostart_var,
            command=lambda: self.app_logic.toggle_autostart()
        ).pack(anchor="w", pady=5)

        minimize_var = ctk.BooleanVar(value=self.app_logic.config.get("start_minimized", False))
        ctk.CTkCheckBox(
            startup_frame,
            text="Start minimized to tray",
            variable=minimize_var,
            command=lambda: self.app_logic.config.set("start_minimized", minimize_var.get())
        ).pack(anchor="w", pady=5)

    def create_appearance_tab(self, parent):
        """Appearance settings"""
        # Theme
        theme_frame = ctk.CTkFrame(parent)
        theme_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(theme_frame, text="Theme",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)

        theme_var = ctk.StringVar(value=self.app_logic.config.get("theme", "dark"))

        ctk.CTkRadioButton(
            theme_frame, text="🌙 Dark", variable=theme_var, value="dark",
            command=lambda: self.app_logic.apply_theme("dark")
        ).pack(anchor="w", pady=2)

        ctk.CTkRadioButton(
            theme_frame, text="☀️ Light", variable=theme_var, value="light",
            command=lambda: self.app_logic.apply_theme("light")
        ).pack(anchor="w", pady=2)

        ctk.CTkRadioButton(
            theme_frame, text="🖥️ System", variable=theme_var, value="system",
            command=lambda: self.app_logic.apply_theme("system")
        ).pack(anchor="w", pady=2)

        # Language
        lang_frame = ctk.CTkFrame(parent)
        lang_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(lang_frame, text="Language",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)

        lang_var = ctk.StringVar(value=self.app_logic.config.get("language", "en"))

        languages = [
            ("🇬🇧 English", "en"),
            ("🇺🇦 Українська", "uk"),
            ("🇩🇪 Deutsch", "de"),
            ("🇵🇱 Polski", "pl"),
            ("🇯🇵 日本語", "ja")
        ]

        for label, code in languages:
            ctk.CTkRadioButton(
                lang_frame, text=label, variable=lang_var, value=code,
                command=lambda c=code: self.app_logic.set_language(c)
            ).pack(anchor="w", pady=2)

    def create_advanced_tab(self, parent):
        """Advanced settings"""
        # Detailed logging
        logging_frame = ctk.CTkFrame(parent)
        logging_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(logging_frame, text="Logging",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)

        detailed_log_var = ctk.BooleanVar(value=self.app_logic.config.get("detailed_logging", False))
        ctk.CTkCheckBox(
            logging_frame,
            text="Enable detailed logging (for debugging)",
            variable=detailed_log_var,
            command=lambda: self.on_detailed_logging_change(detailed_log_var.get())
        ).pack(anchor="w", pady=5)

        ctk.CTkLabel(
            logging_frame,
            text="⚠️ Requires restart. Creates ~10MB/hour of logs.",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).pack(anchor="w", padx=20)

        # Open log folder button
        ctk.CTkButton(
            logging_frame,
            text="📂 Open Log Folder",
            command=self.open_log_folder
        ).pack(fill="x", pady=5)

        # Plugins
        plugin_frame = ctk.CTkFrame(parent)
        plugin_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(plugin_frame, text="Plugins",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)

        ctk.CTkButton(
            plugin_frame,
            text="🔌 Manage Plugins",
            command=self.open_plugin_manager
        ).pack(fill="x", pady=5)

    def open_log_folder(self):
        """Open logs folder in file explorer"""
        import subprocess
        import sys

        log_dir = os.path.abspath('logs')
        os.makedirs(log_dir, exist_ok=True)

        try:
            if sys.platform == 'win32':
                os.startfile(log_dir)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', log_dir])
            else:  # Linux
                subprocess.Popen(['xdg-open', log_dir])
        except Exception as e:
            CTkMessageBox(
                title="Error",
                message=f"Could not open log folder:\n{str(e)}",
                icon="warning"
            )

    def on_detailed_logging_change(self, enabled: bool):
        """Handle detailed logging toggle"""
        self.app_logic.config.set("detailed_logging", enabled)
        CTkMessageBox(
            title="Restart Required",
            message="Please restart VortECIO to apply logging changes.",
            icon="info"
        )

    def open_plugin_manager(self):
        from ui.plugin_manager_window import PluginManagerWindow
        PluginManagerWindow(self, self.app_logic)

    def create_about_tab(self, parent):
        """About information"""
        # Logo/Icon
        ctk.CTkLabel(
            parent,
            text="🌀",
            font=ctk.CTkFont(size=64)
        ).pack(pady=20)

        # App name and version
        ctk.CTkLabel(
            parent,
            text="VortECIO",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack()

        ctk.CTkLabel(
            parent,
            text="Version 1.0.0",
            text_color="gray"
        ).pack()

        # Description
        ctk.CTkLabel(
            parent,
            text="Modern notebook fan control utility\nNBFC-compatible configuration",
            text_color="gray"
        ).pack(pady=10)

        # Links
        ctk.CTkButton(
            parent,
            text="🌐 GitHub Repository",
            command=lambda: webbrowser.open("https://github.com/edhases/VortECIO")
        ).pack(pady=5)

        # Credits
        credits_frame = ctk.CTkFrame(parent)
        credits_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            credits_frame,
            text="Built with: CustomTkinter, LibreHardwareMonitor, pythonnet",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).pack()
