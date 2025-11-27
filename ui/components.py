import customtkinter as ctk

class CTkMessageBox(ctk.CTkToplevel):
    """Custom messagebox using customtkinter"""
    def __init__(self, title: str, message: str, icon: str = "info"):
        super().__init__()
        self.title(title)
        self.geometry("400x200")
        self.transient()  # Make it a modal dialog
        self.grab_set()   # Grab focus

        # Icon
        icon_label = ctk.CTkLabel(self, text="⚠️" if icon == "warning" else "ℹ️",
                                   font=ctk.CTkFont(size=48))
        icon_label.pack(pady=20)

        # Message
        msg_label = ctk.CTkLabel(self, text=message, wraplength=350)
        msg_label.pack(pady=10)

        # OK button
        ctk.CTkButton(self, text="OK", command=self.destroy, width=100).pack(pady=20)
