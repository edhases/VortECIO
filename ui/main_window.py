import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from logger import get_logger
from localization import translate
from ui.plugin_manager_window import PluginManagerWindow

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
        for widget in self.winfo_children():
            widget.destroy()
        self.fan_vars = {}
        self.title(translate("app_title"))
        self.geometry("400x450")
        self.create_widgets()
        if self.app_logic.nbfc_parser.fans:
            self.create_fan_widgets(self.app_logic.nbfc_parser.fans)

    def create_widgets(self):
        # Menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=translate("file_menu"), menu=file_menu)
        file_menu.add_command(label=translate("load_config_menu"), command=self.app_logic.load_config_file)
        file_menu.add_separator()
        file_menu.add_command(label=translate("hide_to_tray_menu"), command=self.app_logic.on_closing)
        file_menu.add_command(label=translate("quit_menu"), command=self.app_logic.quit)
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=translate("settings_menu"), menu=settings_menu)
        theme_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label=translate("theme_menu"), menu=theme_menu)
        theme_menu.add_command(label=translate("theme_light"), command=lambda: self.app_logic.apply_theme("light"))
        theme_menu.add_command(label=translate("theme_dark"), command=lambda: self.app_logic.apply_theme("dark"))
        theme_menu.add_command(label=translate("theme_black"), command=lambda: self.app_logic.apply_theme("black"))
        lang_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label=translate("language_menu"), menu=lang_menu)
        lang_menu.add_command(label=translate("lang_en"), command=lambda: self.app_logic.set_language("en"))
        lang_menu.add_command(label=translate("lang_de"), command=lambda: self.app_logic.set_language("de"))
        lang_menu.add_command(label=translate("lang_pl"), command=lambda: self.app_logic.set_language("pl"))
        lang_menu.add_command(label=translate("lang_uk"), command=lambda: self.app_logic.set_language("uk"))
        lang_menu.add_command(label=translate("lang_ja"), command=lambda: self.app_logic.set_language("ja"))
        settings_menu.add_separator()
        self.autostart_var = tk.BooleanVar(value=self.app_logic.config.get("autostart"))
        settings_menu.add_checkbutton(label=translate("autostart_windows"), variable=self.autostart_var, command=self.app_logic.toggle_autostart)
        plugins_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=translate("plugins_menu"), menu=plugins_menu)
        plugins_menu.add_command(label=translate("manage_plugins_menu"), command=self.open_plugin_manager)

        # Main frame
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(expand=True, fill='both')

        # Temperature display
        temp_frame = ttk.Frame(self.main_frame)
        temp_frame.pack(fill='x', pady=(0, 10))
        self.cpu_temp_var = tk.StringVar(value="CPU: N/A")
        self.gpu_temp_var = tk.StringVar(value="GPU: N/A")
        ttk.Label(temp_frame, textvariable=self.cpu_temp_var, font=("Segoe UI", 12, "bold")).pack(side='left', expand=True)
        ttk.Label(temp_frame, textvariable=self.gpu_temp_var, font=("Segoe UI", 12, "bold")).pack(side='right', expand=True)

        # Fan display frame
        self.fan_display_frame = ttk.Frame(self.main_frame)
        self.fan_display_frame.pack(expand=True, fill='both', pady=5)
        self.msg_label = ttk.Label(self.fan_display_frame, text=translate("no_config_loaded_msg"))
        self.msg_label.pack(pady=20)

        # Status bar
        self.status_bar = ttk.Frame(self, relief='sunken', padding="2 5")
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
            fan_frame.pack(fill='x', padx=5, pady=5, expand=True)

            # Info line (RPM and current percentage)
            info_frame = ttk.Frame(fan_frame)
            info_frame.pack(fill='x')

            rpm_var = tk.StringVar(value="RPM: N/A")
            self.fan_vars[f'fan_{i}_rpm'] = rpm_var
            ttk.Label(info_frame, textvariable=rpm_var).pack(side='left')

            percent_var = tk.StringVar(value="(Auto)")
            self.fan_vars[f'fan_{i}_percent'] = percent_var
            ttk.Label(info_frame, textvariable=percent_var).pack(side='right')

            # Slider
            min_val, max_val = fan['min_speed'], fan['max_speed']
            slider_var = tk.IntVar(value=max_val + 1) # Default to Auto
            self.fan_vars[f'fan_{i}_write'] = slider_var

            slider = ttk.Scale(fan_frame, from_=min_val - 2, to=max_val + 1, orient='horizontal', variable=slider_var,
                               command=lambda v, idx=i: self.update_slider_display(v, idx))
            slider.pack(fill='x', pady=5, expand=True)

            # Apply Button
            apply_button = ttk.Button(fan_frame, text=translate("apply_button"),
                                      command=lambda idx=i: self.app_logic.set_fan_speed(idx))
            apply_button.pack(anchor='e', pady=(5, 0))
            self.fan_vars[f'fan_{i}_apply_button'] = apply_button

            self.update_slider_display(slider_var.get(), i)

    def update_slider_display(self, value, fan_index):
        val = int(float(value))
        fan = self.app_logic.nbfc_parser.fans[fan_index]
        min_val, max_val = fan['min_speed'], fan['max_speed']

        special_modes = {
            min_val - 2: translate("slider_off"),
            min_val - 1: translate("slider_read"),
            max_val + 1: translate("slider_auto")
        }

        # Sync sliders to special modes
        if val in special_modes:
            for i in range(len(self.app_logic.nbfc_parser.fans)):
                if i != fan_index:
                    self.fan_vars.get(f'fan_{i}_write').set(val)

        # Update labels for all fans
        for i in range(len(self.app_logic.nbfc_parser.fans)):
            current_val = self.fan_vars.get(f'fan_{i}_write').get()
            percent_var = self.fan_vars.get(f'fan_{i}_percent')
            if percent_var:
                if current_val in special_modes:
                    percent_var.set(f"({special_modes[current_val]})")
                else:
                    percent_var.set(f"{current_val}%")

    def update_fan_readings(self, fan_index, rpm_value):
        rpm_var = self.fan_vars.get(f'fan_{fan_index}_rpm')
        if rpm_var:
            rpm_var.set(f"RPM: {rpm_value}")

    def update_temps(self, cpu_temp, gpu_temp):
        self.cpu_temp_var.set(f"CPU: {cpu_temp:.1f}°C" if cpu_temp is not None else "CPU: N/A")
        self.gpu_temp_var.set(f"GPU: {gpu_temp:.1f}°C" if gpu_temp is not None else "GPU: N/A")

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def get_selected_filepath(self):
        return filedialog.askopenfilename(
            title=translate("load_config_menu"),
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
