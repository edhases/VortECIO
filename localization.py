import json
import os
import logging

logger = logging.getLogger('FanControl.Localization')

_translations = {}
_current_language = 'en'
_available_languages = {}

def load_languages():
    """Load all language files from the 'lang' directory."""
    global _translations, _available_languages
    lang_dir = 'lang'
    if not os.path.exists(lang_dir):
        logger.error(f"Language directory '{lang_dir}' not found.")
        return

    for filename in os.listdir(lang_dir):
        if filename.endswith('.json'):
            lang_code = filename[:-5]
            filepath = os.path.join(lang_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    _translations[lang_code] = json.load(f)
                    # Assuming the language name is in the file, e.g., "lang_name": "English"
                    # For now, just use the code
                    _available_languages[lang_code] = lang_code
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load language file {filename}: {e}")

    if 'en' not in _translations:
        logger.error("Default language 'en' not found.")

def set_language(lang_code: str):
    """Set the current language for the application."""
    global _current_language
    if lang_code in _translations:
        _current_language = lang_code
    else:
        logger.warning(f"Language '{lang_code}' not found, falling back to 'en'.")
        _current_language = 'en'

def translate(key: str) -> str:
    """Translate a key into the current language."""
    # Try current language first
    translation = _translations.get(_current_language, {}).get(key)
    if translation:
        return translation

    # Fallback to English
    translation = _translations.get('en', {}).get(key)
    if translation:
        logger.warning(f"Translation key '{key}' not found in '{_current_language}', using 'en' fallback.")
        return translation

    # If key not found anywhere
    logger.error(f"Translation key '{key}' not found in any language file.")
    return key

def get_available_languages():
    """Return a dictionary of available language codes and their names."""
    # This can be enhanced to return full names if they are in the JSON files
    return {
        "en": "🇬🇧 English",
        "uk": "🇺🇦 Українська",
        "de": "🇩🇪 Deutsch",
        "pl": "🇵🇱 Polski",
        "ja": "🇯🇵 日本語"
    }

# Initial load
load_languages()
