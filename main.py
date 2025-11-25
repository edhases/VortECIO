import ctypes
import xml.etree.ElementTree as ET
import os
import time
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- EC CONSTANTS (ACPI Standard) ---
EC_SC = 0x66  # Status/Command Port
EC_DATA = 0x62 # Data Port
EC_CMD_READ = 0x80
EC_CMD_WRITE = 0x81
EC_IBF = 0x02 # Input Buffer Full mask
EC_OBF = 0x01 # Output Buffer Full mask

class EcDriver:
    def __init__(self, dll_path='inpoutx64.dll'):
        self.dll_path = dll_path
        self.inpout = None
        self.is_initialized = self._load_driver()

    def _load_driver(self):
        if not os.path.exists(self.dll_path):
            messagebox.showerror("Driver Error", f"{self.dll_path} not found!")
            return False
        try:
            self.inpout = ctypes.windll.LoadLibrary(self.dll_path)
            self.inpout.IsInpOutDriverOpen.restype = ctypes.c_int
            self.inpout.Out32.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
            self.inpout.Inp32.argtypes = [ctypes.c_ushort]
            self.inpout.Inp32.restype = ctypes.c_ushort
            
            if not self.inpout.IsInpOutDriverOpen():
                messagebox.showerror("Driver Error", "Driver not opened. Run as Administrator!")
                return False
            return True
        except Exception as e:
            messagebox.showerror("Driver Error", f"Failed to load driver: {e}")
            return False

    def _wait_ibf(self):
        for _ in range(1000):
            status = self.inpout.Inp32(EC_SC)
            if not (status & EC_IBF):
                return True
            time.sleep(0.001)
        return False

    def _wait_obf(self):
        for _ in range(1000):
            status = self.inpout.Inp32(EC_SC)
            if (status & EC_OBF):
                return True
            time.sleep(0.001)
        return False

    def read_register(self, register):
        if not self.is_initialized: return None
        if not self._wait_ibf(): return None
        self.inpout.Out32(EC_SC, EC_CMD_READ)
        
        if not self._wait_ibf(): return None
        self.inpout.Out32(EC_DATA, register)
        
        if not self._wait_obf(): return None
        return self.inpout.Inp32(EC_DATA)

    def write_register(self, register, value):
        if not self.is_initialized: return False
        if not self._wait_ibf(): return False
        self.inpout.Out32(EC_SC, EC_CMD_WRITE)
        
        if not self._wait_ibf(): return False
        self.inpout.Out32(EC_DATA, register)
        
        if not self._wait_ibf(): return False
        self.inpout.Out32(EC_DATA, value)
        return True

class NbfcConfigParser:
    def __init__(self, xml_file):
        self.file = xml_file
        self.fans = []
        self.model_name = "No config loaded"

    def parse(self):
        if not self.file or not os.path.exists(self.file):
            return False
        try:
            tree = ET.parse(self.file)
            root = tree.getroot()
            
            model_node = root.find('NotebookModel')
            if model_node is not None:
                self.model_name = model_node.text

            self.fans.clear()
            for fan_config in root.findall('.//FanConfiguration'):
                # Find the 'Name' element and get its text, otherwise default
                name_node = fan_config.find('Name')
                fan_name = name_node.text if name_node is not None else 'Unnamed Fan'

                fan = {
                    'name': fan_name,
                    'read_reg': int(fan_config.find('ReadRegister').text),
                    'write_reg': int(fan_config.find('WriteRegister').text),
                    'min_speed': int(fan_config.find('MinSpeedValue').text),
                    'max_speed': int(fan_config.find('MaxSpeedValue').text),
                }
                self.fans.append(fan)
            return True
        except Exception as e:
            messagebox.showerror("XML Parse Error", f"Failed to parse XML: {e}")
            return False

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VortECIO Fan Control")
        self.geometry("450x350")

        self.driver = EcDriver()
        self.config = NbfcConfigParser(None)

        self.fan_vars = {} # To store tk variables for sliders/labels

        self.create_widgets()
        self._create_fan_widgets()
        self.update_fan_readings() # Start the update loop

    def create_widgets(self):
        # Style
        style = ttk.Style(self)
        style.theme_use('clam') #('clam', 'alt', 'default', 'classic')

        # --- Menu ---
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Config", command=self.load_config_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # --- Main Frame ---
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(expand=True, fill='both')
        ttk.Label(self.main_frame, text="Load an NBFC config file via the File menu.").pack(pady=20)

        # --- Status Bar ---
        self.status_bar = ttk.Frame(self, relief='sunken', padding="2 5")
        self.status_bar.pack(side='bottom', fill='x')

        self.model_label = ttk.Label(self.status_bar, text=f"Model: {self.config.model_name}")
        self.model_label.pack(side='left')

        driver_status = "OK" if self.driver.is_initialized else "ERROR"
        self.driver_label = ttk.Label(self.status_bar, text=f"Driver: {driver_status}")
        self.driver_label.pack(side='right')

    def load_config_file(self):
        filepath = filedialog.askopenfilename(
            title="Select NBFC Config File",
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
        if not filepath:
            return

        self.config = NbfcConfigParser(filepath)
        if self.config.parse():
            self.model_label.config(text=f"Model: {self.config.model_name}")
            self._create_fan_widgets()
        else:
            self.config = NbfcConfigParser(None) # Reset on failure
            self.model_label.config(text=f"Model: {self.config.model_name}")

    def _create_fan_widgets(self):
        # Clear existing widgets
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Create new widgets
        for i, fan in enumerate(self.config.fans):
            fan_frame = ttk.LabelFrame(self.main_frame, text=fan['name'], padding="10")
            fan_frame.pack(fill='x', padx=5, pady=5)

            # --- Read Value ---
            read_frame = ttk.Frame(fan_frame)
            read_frame.pack(fill='x')
            ttk.Label(read_frame, text="Current Value:").pack(side='left')

            read_var = tk.StringVar(value="N/A")
            self.fan_vars[f'fan_{i}_read'] = read_var
            ttk.Label(read_frame, textvariable=read_var, width=10).pack(side='left', padx=5)

            # --- Write Value (Slider) ---
            write_frame = ttk.Frame(fan_frame)
            write_frame.pack(fill='x', pady=5)

            min_val, max_val = fan['min_speed'], fan['max_speed']

            slider_var = tk.IntVar(value=min_val)
            self.fan_vars[f'fan_{i}_write'] = slider_var
            
            ttk.Label(write_frame, text=f"Set Value ({min_val}-{max_val}):").pack(side='left')
            
            slider = ttk.Scale(write_frame, from_=min_val, to=max_val, orient='horizontal', variable=slider_var,
                               command=lambda v, i=i: self._update_slider_label(v, i))
            slider.pack(side='left', fill='x', expand=True, padx=5)
            
            slider_label_var = tk.StringVar(value=f"{min_val}")
            self.fan_vars[f'fan_{i}_slider_label'] = slider_label_var
            ttk.Label(write_frame, textvariable=slider_label_var, width=5).pack(side='left')

            # --- Apply Button ---
            apply_button = ttk.Button(fan_frame, text="Apply",
                                     command=lambda i=i: self.set_fan_speed(i))
            apply_button.pack(anchor='e', pady=(5,0))

    def _update_slider_label(self, value, fan_index):
        # Updates the label next to the slider
        val = int(float(value))
        self.fan_vars[f'fan_{fan_index}_slider_label'].set(f"{val}")

    def set_fan_speed(self, fan_index):
        fan = self.config.fans[fan_index]
        write_reg = fan['write_reg']
        value = self.fan_vars[f'fan_{fan_index}_write'].get()

        print(f"Setting fan #{fan_index} (reg: {write_reg}) to {value}")
        success = self.driver.write_register(write_reg, value)
        if not success:
            messagebox.showwarning("Write Error", f"Failed to write to register {write_reg}.")

    def update_fan_readings(self):
        # This is the periodic GUI update function
        if self.config and self.config.fans:
            for i, fan in enumerate(self.config.fans):
                read_reg = fan['read_reg']
                value = self.driver.read_register(read_reg)

                val_str = f"{value}" if value is not None else "ERR"

                if f'fan_{i}_read' in self.fan_vars:
                    self.fan_vars[f'fan_{i}_read'].set(val_str)

        # Schedule the next update (e.g., every 2 seconds)
        self.after(2000, self.update_fan_readings)

def main():
    # Check for admin rights on Windows
    if sys.platform == 'win32':
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False

        if not is_admin:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)

    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
