import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from logger import get_logger
from localization import translate
from ui.plugin_manager_window import PluginManagerWindow

class MainWindow(ctk.CTk):
    def __init__(self, app_logic):
        super().__init__()
        self.app_logic = app_logic
        self.logger = get_logger('MainWindow')
        self.fan_vars = {}

        # Set theme and appearance
        self._set_appearance_mode(self.app_logic.config.get("theme", "dark"))

        self.recreate_ui()
        self.protocol("WM_DELETE_WINDOW", self.app_logic.on_closing)
        self.logger.info("MainWindow initialized")

    def recreate_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.fan_vars = {}
        self.title(translate("app_title"))
        self.geometry("450x550") # Adjusted height after removing graph

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_widgets()

        if self.app_logic.nbfc_parser.fans:
            self.create_fan_widgets(self.app_logic.nbfc_parser.fans)

    def create_widgets(self):
        # Top menu bar frame
        self.menu_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.menu_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        # File Menu
        self.file_menu_var = tk.StringVar(value=translate("file_menu"))
        self.file_menu = ctk.CTkOptionMenu(self.menu_bar, variable=self.file_menu_var,
                                           values=[translate("load_config_menu"), translate("hide_to_tray_menu")],
                                           command=self.file_menu_callback)
        self.file_menu.pack(side="left", padx=(5,0))

        # Settings Menu
        self.settings_menu_var = tk.StringVar(value=translate("settings_menu"))
        self.settings_menu = ctk.CTkOptionMenu(self.menu_bar, variable=self.settings_menu_var,
                                               values=[translate("theme_light"), translate("theme_dark"), "", translate("lang_en"), translate("lang_uk")],
                                               command=self.settings_menu_callback)
        self.settings_menu.pack(side="left", padx=5)

        # Autostart Checkbox
        self.autostart_var = tk.BooleanVar()
        self.autostart_var.set(self.app_logic.config.get("autostart"))
        self.autostart_checkbox = ctk.CTkCheckBox(self.menu_bar, text=translate("autostart_windows"), variable=self.autostart_var, command=self.app_logic.toggle_autostart)
        self.autostart_checkbox.pack(side="left", padx=5)

        # Plugins Menu Button
        self.plugins_menu_button = ctk.CTkButton(self.menu_bar, text=translate("plugins_menu"), width=70, corner_radius=0, command=self.open_plugin_manager)
        self.plugins_menu_button.pack(side="left", padx=0)

        # Quit Button
        self.quit_button = ctk.CTkButton(self.menu_bar, text=translate("quit_menu"), width=60, corner_radius=0, command=self.app_logic.quit)
        self.quit_button.pack(side="right", padx=5)


        # Main frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Temperature display frame
        self.temp_display_frame = ctk.CTkFrame(self.main_frame, corner_radius=5)
        self.temp_display_frame.pack(fill='x', padx=5, pady=5)

        self.cpu_temp_label = ctk.CTkLabel(self.temp_display_frame, text="CPU: N/A", font=ctk.CTkFont(size=14, weight="bold"))
        self.cpu_temp_label.pack(side="left", padx=10, pady=5)

        self.gpu_temp_label = ctk.CTkLabel(self.temp_display_frame, text="GPU: N/A", font=ctk.CTkFont(size=14, weight="bold"))
        self.gpu_temp_label.pack(side="right", padx=10, pady=5)

        # Fan display frame - will be populated later
        self.fan_display_frame = ctk.CTkFrame(self.main_frame, corner_radius=0, fg_color="transparent")
        self.fan_display_frame.pack(expand=True, fill='both', pady=5)

        self.msg_label = ctk.CTkLabel(self.fan_display_frame, text=translate("no_config_loaded_msg"))
        self.msg_label.pack(pady=20)

        # Status bar
        self.status_bar = ctk.CTkFrame(self, height=25, corner_radius=0)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

        self.model_label = ctk.CTkLabel(self.status_bar, text=f"{translate('model_label')}: {self.app_logic.nbfc_parser.model_name}")
        self.model_label.pack(side='left', padx=10)

        driver_status = "OK" if self.app_logic.driver.is_initialized else "ERROR"
        self.driver_label = ctk.CTkLabel(self.status_bar, text=f"{translate('driver_label')}: {driver_status}")
        self.driver_label.pack(side='right', padx=10)

    def file_menu_callback(self, choice):
        if choice == translate("load_config_menu"):
            self.app_logic.load_config_file()
        elif choice == translate("hide_to_tray_menu"):
            self.app_logic.on_closing()
        self.file_menu_var.set(translate("file_menu"))

    def settings_menu_callback(self, choice):
        if choice == translate("theme_light"):
            self.app_logic.apply_theme("light")
        elif choice == translate("theme_dark"):
            self.app_logic.apply_theme("dark")
        elif choice == translate("lang_en"):
            self.app_logic.set_language("en")
        elif choice == translate("lang_uk"):
            self.app_logic.set_language("uk")
        self.settings_menu_var.set(translate("settings_menu"))

    def open_plugin_manager(self):
        PluginManagerWindow(self, self.app_logic)

    def create_fan_widgets(self, fans):
        for widget in self.fan_display_frame.winfo_children():
            widget.destroy()

        if not fans:
            self.msg_label = ctk.CTkLabel(self.fan_display_frame, text=translate("no_fans_found_msg"))
            self.msg_label.pack(pady=20)
            return

        for i, fan in enumerate(fans):
            fan_frame = ctk.CTkFrame(self.fan_display_frame, corner_radius=5)
            fan_frame.pack(fill='x', padx=5, pady=5, ipady=10)
            fan_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(fan_frame, text=fan['name'], font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(5,10))

            # Current speed display
            ctk.CTkLabel(fan_frame, text=translate("current_speed_rpm_label")).grid(row=1, column=0, sticky="w", padx=10)
            read_var = tk.StringVar(value="N/A")
            self.fan_vars[f'fan_{i}_read'] = read_var
            ctk.CTkLabel(fan_frame, textvariable=read_var).grid(row=1, column=1, sticky="w", padx=5)

            # Current percentage display
            percent_var = tk.StringVar(value="(Auto)")
            self.fan_vars[f'fan_{i}_percent'] = percent_var
            ctk.CTkLabel(fan_frame, textvariable=percent_var, font=ctk.CTkFont(size=12, slant="italic")).grid(row=1, column=2, sticky="e", padx=10)

            # Manual control slider
            min_val, max_val = fan['min_speed'], fan['max_speed']
            auto_val = max_val + 1 # Special value for Auto

            slider_var = tk.IntVar(value=auto_val)
            self.fan_vars[f'fan_{i}_write'] = slider_var

            slider = ctk.CTkSlider(fan_frame, from_=min_val, to=auto_val, variable=slider_var,
                                   command=lambda v, idx=i: self.update_slider_label(v, idx))
            slider.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
            self.fan_vars[f'fan_{i}_slider'] = slider

            slider_label_var = tk.StringVar(value="Auto")
            self.fan_vars[f'fan_{i}_slider_label'] = slider_label_var
            ctk.CTkLabel(fan_frame, textvariable=slider_label_var, width=40).grid(row=2, column=2, padx=5)

            apply_button = ctk.CTkButton(fan_frame, text=translate("apply_button"),
                                         command=lambda idx=i: self.app_logic.set_fan_speed(idx))
            apply_button.grid(row=3, column=2, sticky="e", padx=10, pady=(0, 10))
            self.fan_vars[f'fan_{i}_apply_button'] = apply_button

    def update_slider_label(self, value, fan_index):
        val = int(float(value))

        first_fan = self.app_logic.nbfc_parser.fans[0]
        max_val = first_fan['max_speed']
        auto_val = max_val + 1

        is_auto_mode = (val == auto_val)

        for i, fan in enumerate(self.app_logic.nbfc_parser.fans):
            slider_var = self.fan_vars.get(f'fan_{i}_write')
            label_var = self.fan_vars.get(f'fan_{i}_slider_label')

            if not slider_var or not label_var:
                continue

            # Sync sliders to auto mode
            if i != fan_index and is_auto_mode and slider_var.get() != val:
                slider_var.set(val)

            current_val_for_label = slider_var.get()
            if current_val_for_label == auto_val:
                label_var.set(translate("slider_auto"))
            else:
                label_var.set(f"{current_val_for_label}%")

    def update_fan_readings(self, fan_index, rpm_value, percent_value):
        if f'fan_{fan_index}_read' in self.fan_vars:
            self.fan_vars[f'fan_{fan_index}_read'].set(f"{rpm_value}")
        if f'fan_{fan_index}_percent' in self.fan_vars:
            slider_var = self.fan_vars.get(f'fan_{fan_index}_write')
            is_auto = slider_var.get() == self.app_logic.nbfc_parser.fans[fan_index]['max_speed'] + 1 if slider_var else False
            mode_str = translate("slider_auto") if is_auto else ""
            self.fan_vars[f'fan_{fan_index}_percent'].set(f"({percent_value}% {mode_str})")

    def update_temp_readings(self, cpu_temp, gpu_temp):
        self.cpu_temp_label.configure(text=f"CPU: {cpu_temp}°C" if cpu_temp is not None else "CPU: N/A")
        self.gpu_temp_label.configure(text=f"GPU: {gpu_temp}°C" if gpu_temp is not None else "GPU: N/A")

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def get_selected_filepath(self):
        return filedialog.askopenfilename(
            title=translate("load_config_menu"),
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
