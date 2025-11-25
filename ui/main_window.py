import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from logger import get_logger
from localization import translate
from ui.plugin_manager_window import PluginManagerWindow
from ui.temperature_graph import TemperatureGraph

class MainWindow(tk.Tk):
    def __init__(self, app_logic):
        super().__init__()
        self.app_logic = app_logic
        self.logger = get_logger('MainWindow')
        self.style = ttk.Style(self)
        self.fan_vars = {}
        self.recreate_ui()
        self.protocol("WM_DELETE_WINDOW", self.app_logic.on_closing)
        self.logger.info("MainWindow initialized")

    def recreate_ui(self):
        # Destroy all widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Reset fan_vars
        self.fan_vars = {}

        # Set window title
        self.title(translate("app_title"))
        self.geometry("450x600")

        self.create_widgets()

        # If a config is loaded, recreate the fan widgets too
        if self.app_logic.nbfc_parser.fans:
            self.create_fan_widgets(self.app_logic.nbfc_parser.fans)

    def create_widgets(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=translate("file_menu"), menu=file_menu)
        file_menu.add_command(label=translate("load_config_menu"), command=self.app_logic.load_config_file)
        file_menu.add_separator()
        file_menu.add_command(label=translate("hide_to_tray_menu"), command=self.app_logic.on_closing)
        file_menu.add_command(label=translate("quit_menu"), command=self.app_logic.quit)

        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=translate("settings_menu"), menu=settings_menu)

        # Theme Submenu
        theme_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label=translate("theme_menu"), menu=theme_menu)
        theme_menu.add_command(label=translate("theme_light"), command=lambda: self.app_logic.apply_theme("light"))
        theme_menu.add_command(label=translate("theme_dark"), command=lambda: self.app_logic.apply_theme("dark"))
        theme_menu.add_command(label=translate("theme_black"), command=lambda: self.app_logic.apply_theme("black"))

        # Language Submenu
        lang_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label=translate("language_menu"), menu=lang_menu)
        lang_menu.add_command(label=translate("lang_en"), command=lambda: self.app_logic.set_language("en"))
        lang_menu.add_command(label=translate("lang_de"), command=lambda: self.app_logic.set_language("de"))
        lang_menu.add_command(label=translate("lang_pl"), command=lambda: self.app_logic.set_language("pl"))
        lang_menu.add_command(label=translate("lang_uk"), command=lambda: self.app_logic.set_language("uk"))
        lang_menu.add_command(label=translate("lang_ja"), command=lambda: self.app_logic.set_language("ja"))

        settings_menu.add_separator()
        self.autostart_var = tk.BooleanVar()
        self.autostart_var.set(self.app_logic.config.get("autostart"))
        settings_menu.add_checkbutton(label=translate("autostart_windows"), variable=self.autostart_var, command=self.app_logic.toggle_autostart)

        # Plugins Menu
        plugins_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=translate("plugins_menu"), menu=plugins_menu)
        plugins_menu.add_command(label=translate("manage_plugins_menu"), command=self.open_plugin_manager)

        # Main frame
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(expand=True, fill='both')

        # Fan display frame - will be populated later
        self.fan_display_frame = ttk.Frame(self.main_frame)
        self.fan_display_frame.pack(expand=True, fill='both', pady=5)

        self.msg_label = ttk.Label(self.fan_display_frame, text=translate("no_config_loaded_msg"))
        self.msg_label.pack(pady=20)

        # Temperature Graph
        theme_colors = {
            'background': self.style.lookup('TFrame', 'background'),
            'foreground': self.style.lookup('TLabel', 'foreground'),
            'line': '#00ff00'  # Or another color from the theme if available
        }
        self.temp_graph = TemperatureGraph(self.main_frame, theme_colors=theme_colors, height=100)
        self.temp_graph.pack(fill='x', pady=10)

        # Status bar
        self.status_bar = ttk.Frame(self, relief='sunken', padding="2 5", style="StatusBar.TFrame")
        self.status_bar.pack(side='bottom', fill='x')

        self.model_label = ttk.Label(self.status_bar, text=f"{translate('model_label')}: {self.app_logic.nbfc_parser.model_name}")
        self.model_label.pack(side='left')

        driver_status = "OK" if self.app_logic.driver.is_initialized else "ERROR"
        self.driver_label = ttk.Label(self.status_bar, text=f"{translate('driver_label')}: {driver_status}")
        self.driver_label.pack(side='right')

    def open_plugin_manager(self):
        PluginManagerWindow(self, self.app_logic)

    def create_fan_widgets(self, fans):
        for widget in self.fan_display_frame.winfo_children():
            widget.destroy()

        if not fans:
            self.msg_label = ttk.Label(self.fan_display_frame, text=translate("no_fans_found_msg"))
            self.msg_label.pack(pady=20)
            return

        for i, fan in enumerate(fans):
            fan_frame = ttk.LabelFrame(self.fan_display_frame, text=fan['name'], padding="10")
            fan_frame.pack(fill='x', padx=5, pady=5)

            # Read-only value (RPM)
            read_frame = ttk.Frame(fan_frame)
            read_frame.pack(fill='x')
            ttk.Label(read_frame, text=translate("current_speed_rpm_label")).pack(side='left')
            read_var = tk.StringVar(value="N/A")
            self.fan_vars[f'fan_{i}_read'] = read_var
            ttk.Label(read_frame, textvariable=read_var, width=15).pack(side='left', padx=5)

            # Manual control slider
            write_frame = ttk.Frame(fan_frame)
            write_frame.pack(fill='x', pady=5)

            min_val, max_val = fan['min_speed'], fan['max_speed']
            disabled_val = min_val - 2
            read_only_val = min_val - 1
            auto_val = max_val + 1
            slider_var = tk.IntVar(value=auto_val) # Default to Auto
            self.fan_vars[f'fan_{i}_write'] = slider_var

            label_text = translate("set_speed_label").format(min=min_val, max=max_val)
            ttk.Label(write_frame, text=label_text).pack(side='left')

            slider = ttk.Scale(write_frame, from_=disabled_val, to=auto_val, orient='horizontal', variable=slider_var,
                               command=lambda v, idx=i: self.update_slider_label(v, idx))
            slider.pack(side='left', fill='x', expand=True, padx=5)
            self.fan_vars[f'fan_{i}_slider'] = slider

            slider_label_var = tk.StringVar(value="Auto")
            self.fan_vars[f'fan_{i}_slider_label'] = slider_label_var
            ttk.Label(write_frame, textvariable=slider_label_var, width=5).pack(side='left')

            apply_button = ttk.Button(fan_frame, text=translate("apply_button"),
                                      command=lambda idx=i: self.app_logic.set_fan_speed(idx))
            apply_button.pack(anchor='e', pady=(5, 0))
            self.fan_vars[f'fan_{i}_apply_button'] = apply_button

    def update_slider_label(self, value, fan_index):
        val = int(float(value))

        # Determine the special values from the first fan's config
        # (assuming they are consistent across all fans)
        first_fan = self.app_logic.nbfc_parser.fans[0]
        min_val = first_fan['min_speed']
        max_val = first_fan['max_speed']
        disabled_val = min_val - 2
        read_only_val = min_val - 1
        auto_val = max_val + 1

        is_special_mode = val in [disabled_val, read_only_val, auto_val]

        for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
            slider_var = self.fan_vars.get(f'fan_{i}_write')
            label_var = self.fan_vars.get(f'fan_{i}_slider_label')

            if not slider_var or not label_var:
                continue

            current_slider_val = slider_var.get()

            # If a special mode is set on the triggering slider, sync all sliders
            if i != fan_index and is_special_mode and current_slider_val != val:
                slider_var.set(val)

            # Update label for the current slider (whether it's the trigger or not)
            current_val_for_label = slider_var.get()
            if current_val_for_label == auto_val:
                label_var.set(translate("slider_auto"))
            elif current_val_for_label == read_only_val:
                label_var.set(translate("slider_read"))
            elif current_val_for_label == disabled_val:
                label_var.set(translate("slider_off"))
            else:
                label_var.set(f"{current_val_for_label}")

    def update_fan_readings(self, fan_index, value):
        if f'fan_{fan_index}_read' in self.fan_vars:
            self.fan_vars[f'fan_{fan_index}_read'].set(f"{value}")

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def get_selected_filepath(self):
        return filedialog.askopenfilename(
            title=translate("load_config_menu"),
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
