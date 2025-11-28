import os
from pystray import Icon, MenuItem, Menu
from PIL import Image
from localization import translate

class SystemTray:
    def __init__(self, app_logic):
        self.app_logic = app_logic
        self.icon = None

    def create_icon(self):
        icon_image = None
        if os.path.exists("app.ico"):
            try:
                icon_image = Image.open("app.ico")
            except Exception as e:
                print(f"Failed to load app.ico: {e}")

        if not icon_image:
            # Create a dummy image for the icon if app.ico is not found
            icon_image = Image.new('RGB', (64, 64), 'black')

        menu = Menu(
            MenuItem(lambda text: translate("tray_show"), self.on_show),
            MenuItem(lambda text: translate("tray_quit"), self.on_exit)
        )

        self.icon = Icon("VortECIO", icon_image, "VortECIO Fan Control", menu)

        # Run the icon in a separate thread
        import threading
        self.icon_thread = threading.Thread(target=self.icon.run)
        self.icon_thread.daemon = True
        self.icon_thread.start()

    def on_show(self, icon, item):
        self.app_logic.main_window.deiconify()

    def on_exit(self, icon, item):
        self.icon.stop()
        self.app_logic.quit()
