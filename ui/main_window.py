import customtkinter as ctk
from customtkinter import filedialog
from logger import get_logger
from localization import translate
from ui.plugin_manager_window import PluginManagerWindow
from CTkToolTip import CTkToolTip
from ui.components import CTkMessageBox

class StatusNotification(ctk.CTkToplevel):
    """Toast-style notification window"""
    def __init__(self, parent, message: str, duration: int = 3000):
        super().__init__(parent)

        # Make it a borderless, tool window
        self.overrideredirect(True)
        self.wm_attributes("-toolwindow", True)
        self.attributes('-topmost', True) # Keep on top

        # Use a frame inside for styling
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.pack(expand=True, fill="both")

        label = ctk.CTkLabel(frame, text=message)
        label.pack(padx=20, pady=10)

        # Force window to calculate its size
        self.update_idletasks()

        # Position at bottom-right of parent
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        self_w = self.winfo_width()
        self_h = self.winfo_height()

        pos_x = parent_x + parent_w - self_w - 20
        pos_y = parent_y + parent_h - self_h - 20
        self.geometry(f"{self_w}x{self_h}+{pos_x}+{pos_y}")

        # Set initial alpha and start fade-in
        self.attributes('-alpha', 0.0)
        self.after(10, self.animate_show)

        # Auto-hide after duration
        self.after(duration, self.animate_hide)

    def animate_show(self):
        """Fade in animation"""
        alpha = 0.0
        def fade():
            nonlocal alpha
            alpha += 0.1
            if alpha >= 1.0:
                self.attributes('-alpha', 1.0)
            else:
                self.attributes('-alpha', alpha)
                self.after(20, fade)
        fade()

    def animate_hide(self):
        """Fade out animation"""
        alpha = 1.0
        def fade():
            nonlocal alpha
            alpha -= 0.1
            if alpha <= 0:
                self.destroy()
            else:
                self.attributes('-alpha', alpha)
                self.after(20, fade)
        fade()


class MainWindow(ctk.CTk):
    def __init__(self, app_logic):
        super().__init__()
        self.app_logic = app_logic
        self.logger = get_logger('MainWindow')
        self.fan_vars = {}
        self.fan_mode_vars = {}
        self.fan_slider_vars = {}
        self.fan_sliders = {}
        self.fan_speed_labels = {}
        self.fan_rpm_labels = {}
        self.fan_frames = {}
        self.mode_indicators = {}

        self.autostart_var = ctk.BooleanVar(value=self.app_logic.config.get("autostart", False))

        # Set theme and appearance
        ctk.set_appearance_mode(self.app_logic.config.get("theme", "dark"))

        self.recreate_ui()
        self.protocol("WM_DELETE_WINDOW", self.app_logic.on_closing)
        self.logger.info("MainWindow initialized")

    def recreate_ui(self):
        # Cancel all debounce timers
        for attr in dir(self):
            if attr.startswith('_slider_timer_'):
                timer_id = getattr(self, attr, None)
                if timer_id:
                    try:
                        self.after_cancel(timer_id)
                    except Exception:
                        pass  # Timer may have already fired or be invalid

        for widget in self.winfo_children():
            widget.destroy()

        self.fan_vars = {}
        self.fan_mode_vars = {}
        self.fan_slider_vars = {}
        self.fan_sliders = {}
        self.fan_speed_labels = {}
        self.fan_rpm_labels = {}

        self.title(translate("app_title"))
        self.geometry("600x400") # Adjusted height and width

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.create_top_bar()
        self.create_status_bar()
        self.create_fan_controls()
        self.create_bottom_bar()

        if self.app_logic.nbfc_parser.fans:
            self.create_fan_widgets(self.app_logic.nbfc_parser.fans)

    def create_top_bar(self):
        """Minimal top bar with title and settings"""
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)

        # Title
        title = ctk.CTkLabel(
            top_frame,
            text=translate('app_title'),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(side="left")

        # Settings button (replaces entire menu bar)
        settings_btn = ctk.CTkButton(
            top_frame,
            text="⚙️ Settings",
            width=100,
            command=self.open_settings
        )
        settings_btn.pack(side="right")

    def create_status_bar(self):
        """Compact status indicators"""
        status_frame = ctk.CTkFrame(self, height=50)
        status_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)

        # Temperature indicators
        self.cpu_temp_label = ctk.CTkLabel(
            status_frame,
            text="🌡️ CPU: --°C",
            font=ctk.CTkFont(size=14)
        )
        self.cpu_temp_label.pack(side="left", padx=20)

        self.gpu_temp_label = ctk.CTkLabel(
            status_frame,
            text="🎮 GPU: --°C",
            font=ctk.CTkFont(size=14)
        )
        self.gpu_temp_label.pack(side="left", padx=20)

        # Driver status indicator
        self.driver_indicator = ctk.CTkLabel(
            status_frame,
            text="🔧 OK" if self.app_logic.driver.is_initialized else "❌ ERROR",
            font=ctk.CTkFont(size=14),
            text_color="green" if self.app_logic.driver.is_initialized else "red"
        )
        self.driver_indicator.pack(side="right", padx=20)

    def create_fan_controls(self):
        # Fan display frame - will be populated later
        self.fan_display_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fan_display_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.fan_display_frame.grid_columnconfigure(0, weight=1)

        self.msg_label = ctk.CTkLabel(self.fan_display_frame, text=translate("no_config_loaded_msg"))
        self.msg_label.pack(pady=20)

    def create_bottom_bar(self):
        # Status bar
        self.status_bar = ctk.CTkFrame(self, height=25, corner_radius=0)
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=0, pady=0)

        self.model_label = ctk.CTkLabel(self.status_bar, text=f"{translate('model_label')}: {self.app_logic.nbfc_parser.model_name}")
        self.model_label.pack(side='left', padx=10)

    def open_settings(self):
        from ui.settings_window import SettingsWindow
        if not hasattr(self, 'settings_window') or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, self.app_logic)

    def create_fan_widgets(self, fans):
        for widget in self.fan_display_frame.winfo_children():
            widget.destroy()

        if not fans:
            self.msg_label = ctk.CTkLabel(self.fan_display_frame, text=translate("no_fans_found_msg"))
            self.msg_label.pack(pady=20)
            return

        for i, fan in enumerate(fans):
            self.create_fan_control(fan, i)

    def create_fan_control(self, fan_config: dict, fan_index: int):
        """Create modern fan control widget"""
        fan_frame = ctk.CTkFrame(self.fan_display_frame)
        fan_frame.pack(fill="x", padx=20, pady=10)
        self.fan_frames[fan_index] = fan_frame

        # Header with name and mode selector
        header_frame = ctk.CTkFrame(fan_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)

        mode_indicator = ctk.CTkLabel(header_frame, text="🤖", font=ctk.CTkFont(size=20))
        mode_indicator.pack(side="left", padx=(0, 5))
        self.mode_indicators[fan_index] = mode_indicator

        fan_name = ctk.CTkLabel(
            header_frame,
            text=f"{fan_config['name']}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        fan_name.pack(side="left")

        # Mode selector (dropdown) ✅
        mode_var = ctk.StringVar(value="Auto")
        self.fan_mode_vars[fan_index] = mode_var

        mode_selector = ctk.CTkOptionMenu(
            header_frame,
            variable=mode_var,
            values=["Auto", "Manual", "Read-only", "Disabled"],
            width=120,
            command=lambda choice, idx=fan_index: self.on_mode_change(idx, choice)
        )
        mode_selector.pack(side="right")

        # Slider (only for Manual mode) ✅
        slider_frame = ctk.CTkFrame(fan_frame, fg_color="transparent")
        slider_frame.pack(fill="x", padx=10, pady=5)

        slider_var = ctk.IntVar(value=50)
        self.fan_slider_vars[fan_index] = slider_var

        slider = ctk.CTkSlider(
            slider_frame,
            from_=0, to=100,  # Normal 0-100%, no magic values! ✅
            variable=slider_var,
            command=lambda v, idx=fan_index: self.on_slider_change(idx, v)
        )
        slider.pack(side="left", fill="x", expand=True, padx=5)
        self.fan_sliders[fan_index] = slider

        # Initially disable slider (Auto mode)
        slider.configure(state="disabled")

        CTkToolTip(mode_selector, message="Auto: Control based on temperature curve\nManual: Set fixed speed\nRead-only: Monitor only\nDisabled: Use BIOS control")
        CTkToolTip(slider, message="Drag to adjust fan speed (0-100%)")

        # Value labels
        speed_label = ctk.CTkLabel(slider_frame, text="50%", width=50)
        speed_label.pack(side="left", padx=5)
        self.fan_speed_labels[fan_index] = speed_label

        rpm_label = ctk.CTkLabel(slider_frame, text="-- RPM", width=80)
        rpm_label.pack(side="left", padx=5)
        self.fan_rpm_labels[fan_index] = rpm_label

    def on_mode_change(self, fan_index: int, mode: str):
        """Handle mode change"""
        slider = self.fan_sliders[fan_index]

        if mode == "Manual":
            slider.configure(state="normal")  # Enable slider
        else:
            slider.configure(state="disabled")  # Disable slider

        # Apply mode to backend
        self.app_logic.set_fan_mode(fan_index, mode)
        self.update_fan_display(fan_index, mode)

    def update_fan_display(self, fan_index: int, mode: str):
        """Update visual appearance based on mode"""
        frame = self.fan_frames[fan_index]

        # Color coding
        colors = {
            'Auto': ('green', '🤖'),
            'Manual': ('blue', '👤'),
            'Read-only': ('gray', '👁️'),
            'Disabled': ('red', '⏸️')
        }

        color, icon = colors[mode]
        frame.configure(border_color=color, border_width=2)

        # Update mode indicator
        self.mode_indicators[fan_index].configure(text=icon)

    def on_slider_change(self, fan_index: int, value: float):
        """Handle slider change in real-time"""
        mode = self.fan_mode_vars[fan_index].get()

        if mode == "Manual":
            # Apply immediately with debounce
            if hasattr(self, f'_slider_timer_{fan_index}'):
                self.after_cancel(getattr(self, f'_slider_timer_{fan_index}'))

            # Debounce: apply after 200ms of no changes
            timer = self.after(200, lambda: self.app_logic.set_manual_fan_speed(fan_index, int(value)))
            setattr(self, f'_slider_timer_{fan_index}', timer)

        self.fan_speed_labels[fan_index].configure(text=f"{int(value)}%")


    def update_fan_readings(self, fan_index, rpm_value, percent_value):
        if fan_index in self.fan_rpm_labels:
            self.fan_rpm_labels[fan_index].configure(text=f"{rpm_value} RPM")
        if fan_index in self.fan_speed_labels and self.fan_mode_vars[fan_index].get() != "Manual":
            self.fan_speed_labels[fan_index].configure(text=f"{percent_value}%")

    def update_temp_readings(self, cpu_temp, gpu_temp):
        cpu_text = f"CPU: {int(cpu_temp)}°C" if cpu_temp is not None else "CPU: N/A"
        gpu_text = f"GPU: {int(gpu_temp)}°C" if gpu_temp is not None else "GPU: N/A"
        self.cpu_temp_label.configure(text=cpu_text)
        self.gpu_temp_label.configure(text=gpu_text)

    def show_error(self, title, message):
        CTkMessageBox(title, message, icon="warning")

    def get_selected_filepath(self):
        return filedialog.askopenfilename(
            title=translate("load_config_menu"),
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
