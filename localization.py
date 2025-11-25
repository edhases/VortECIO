LOCALIZATION = {
    "en": {
        "app_title": "VortECIO Fan Control",
        "file_menu": "File",
        "load_config_menu": "Load Config",
        "exit_menu": "Exit",
        "settings_menu": "Settings",
        "theme_menu": "Theme",
        "language_menu": "Language",
        "fan_control_mode_label": "Fan Control Mode",
        "disabled_mode": "Disabled",
        "read_only_mode": "Read-only",
        "automatic_mode": "Automatic",
        "no_config_loaded_msg": "Load an NBFC config file via the File menu.",
        "model_label": "Model",
        "driver_label": "Driver",
        "current_value_label": "Current Value",
        "set_speed_label": "Set ({min}-{max})",
        "apply_button": "Apply"
    },
    "uk": {
        "app_title": "VortECIO Керування Вентиляторами",
        "file_menu": "Файл",
        "load_config_menu": "Завантажити конфіг",
        "exit_menu": "Вихід",
        "settings_menu": "Налаштування",
        "theme_menu": "Тема",
        "language_menu": "Мова",
        "fan_control_mode_label": "Режим керування",
        "disabled_mode": "Вимкнено",
        "read_only_mode": "Тільки читання",
        "automatic_mode": "Автоматично",
        "no_config_loaded_msg": "Завантажте конфіг NBFC через меню 'Файл'.",
        "model_label": "Модель",
        "driver_label": "Драйвер",
        "current_value_label": "Поточне значення",
        "set_speed_label": "Встановити ({min}-{max})",
        "apply_button": "Застосувати"
    },
    "de": {
        "app_title": "VortECIO Lüftersteuerung",
        "file_menu": "Datei",
        "load_config_menu": "Konfiguration laden",
        "exit_menu": "Beenden",
        "settings_menu": "Einstellungen",
        "theme_menu": "Thema",
        "language_menu": "Sprache",
        "fan_control_mode_label": "Lüftersteuerungsmodus",
        "disabled_mode": "Deaktiviert",
        "read_only_mode": "Nur Lesen",
        "automatic_mode": "Automatisch",
        "no_config_loaded_msg": "Laden Sie eine NBFC-Konfigurationsdatei über das Menü 'Datei'.",
        "model_label": "Modell",
        "driver_label": "Treiber",
        "current_value_label": "Aktueller Wert",
        "set_speed_label": "Einstellen ({min}-{max})",
        "apply_button": "Anwenden"
    },
    "pl": {
        "app_title": "VortECIO Kontrola Wentylatorów",
        "file_menu": "Plik",
        "load_config_menu": "Załaduj konfigurację",
        "exit_menu": "Wyjście",
        "settings_menu": "Ustawienia",
        "theme_menu": "Motyw",
        "language_menu": "Język",
        "fan_control_mode_label": "Tryb kontroli wentylatorów",
        "disabled_mode": "Wyłączony",
        "read_only_mode": "Tylko do odczytu",
        "automatic_mode": "Automatyczny",
        "no_config_loaded_msg": "Załaduj plik konfiguracyjny NBFC z menu 'Plik'.",
        "model_label": "Model",
        "driver_label": "Sterownik",
        "current_value_label": "Aktualna wartość",
        "set_speed_label": "Ustaw ({min}-{max})",
        "apply_button": "Zastosuj"
    },
    "ja": {
        "app_title": "VortECIO ファンコントロール",
        "file_menu": "ファイル",
        "load_config_menu": "設定を読み込む",
        "exit_menu": "終了",
        "settings_menu": "設定",
        "theme_menu": "テーマ",
        "language_menu": "言語",
        "fan_control_mode_label": "ファン制御モード",
        "disabled_mode": "無効",
        "read_only_mode": "読み取り専用",
        "automatic_mode": "自動",
        "no_config_loaded_msg": "「ファイル」メニューからNBFC設定ファイルを読み込んでください。",
        "model_label": "モデル",
        "driver_label": "ドライバー",
        "current_value_label": "現在の値",
        "set_speed_label": "設定 ({min}-{max})",
        "apply_button": "適用"
    }
}

class Translator:
    def __init__(self, language="en"):
        self.language = language

    def set_language(self, language):
        self.language = language

    def get(self, key):
        return LOCALIZATION.get(self.language, LOCALIZATION["en"]).get(key, key)

# Global translator instance
translator = Translator()

def set_language(language_code):
    translator.set_language(language_code)

def translate(key):
    return translator.get(key)
