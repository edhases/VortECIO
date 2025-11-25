import tkinter as tk
from tkinter import messagebox

class ExamplePlugin:
    def __init__(self, app_logic):
        self.app_logic = app_logic

    def initialize(self):
        # This is a simple implementation. A more robust solution would involve
        # a centralized menu manager to prevent duplicate menus.
        main_window = self.app_logic.main_window
        menubar = main_window.nametowidget(main_window['menu'])

        plugin_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plugins", menu=plugin_menu)

        plugin_menu.add_command(label="Hello Plugin", command=self.show_hello_message)

    def show_hello_message(self):
        messagebox.showinfo("Example Plugin", "Hello from the example plugin!")

    def shutdown(self):
        print("Example plugin is shutting down.")


def register(app_logic):
    # This function is called by the plugin manager to register the plugin
    return ExamplePlugin(app_logic)
