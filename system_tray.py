from pystray import Icon, MenuItem, Menu
from PIL import Image

class SystemTray:
    def __init__(self, app_logic):
        self.app_logic = app_logic
        self.icon = None

    def create_icon(self):
        # Create a dummy image for the icon
        image = Image.new('RGB', (64, 64), 'black')

        menu = Menu(
            MenuItem('Show', self.on_show),
            MenuItem('Exit', self.on_exit)
        )

        self.icon = Icon("VortECIO", image, "VortECIO Fan Control", menu)

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
