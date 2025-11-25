THEMES = {
    "light": {
        "background": "#ECECEC",
        "foreground": "#000000",
        "troughcolor": "#DCDCDC",
        "frame_bg": "#F0F0F0",
        "button_bg": "#E0E0E0"
    },
    "dark": {
        "background": "#2E2E2E",
        "foreground": "#FFFFFF",
        "troughcolor": "#3C3C3C",
        "frame_bg": "#383838",
        "button_bg": "#505050"
    },
    "black": {
        "background": "#000000",
        "foreground": "#00FF00",
        "troughcolor": "#1A1A1A",
        "frame_bg": "#101010",
        "button_bg": "#202020"
    }
}

def apply_theme(root, theme_name):
    theme = THEMES.get(theme_name, THEMES['light'])

    style = root.style

    # Configure the theme for ttk widgets
    style.theme_use('clam')

    # Root window
    root.configure(bg=theme['background'])

    # ttk styles
    style.configure('.', background=theme['background'], foreground=theme['foreground'])
    style.configure('TFrame', background=theme['background'])
    style.configure('TLabel', background=theme['background'], foreground=theme['foreground'])
    style.configure('TRadiobutton', background=theme['background'], foreground=theme['foreground'])
    style.configure('TButton', background=theme['button_bg'], foreground=theme['foreground'])
    style.map('TButton', background=[('active', theme['frame_bg'])])

    # Special handling for Scale widget trough color
    style.configure('Horizontal.TScale', troughcolor=theme['troughcolor'],
                    background=theme['background'], foreground=theme['foreground'])

    # LabelFrame background can't be set directly via style in some Tk versions.
    # We will need to set it on the widget itself.
    style.configure('TLabelframe', background=theme['frame_bg'], bordercolor=theme['foreground'])
    style.configure('TLabelframe.Label', background=theme['frame_bg'], foreground=theme['foreground'])

    # Status bar
    style.configure('StatusBar.TFrame', background=theme['frame_bg'])
