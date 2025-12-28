import { writable, get } from 'svelte/store';
import { GetSettings } from '../../wailsjs/go/main/App';
import en from './en.json';
import ua from './ua.json';
import de from './de.json';
import ja from './ja.json';
import pl from './pl.json';

const translations = { en, ua, de, ja, pl };

// Fallback language
const defaultLocale = 'en';

// Create a writable store
export const locale = writable(defaultLocale);
export const t = writable(translations[defaultLocale]);

// Function to initialize the store from backend settings
export async function initI18n() {
    try {
        const settings = await GetSettings();
        const lang = settings.Language || defaultLocale;
        if (translations[lang]) {
            locale.set(lang);
            t.set(translations[lang]);
        } else {
            console.warn(`Language '${lang}' not found, falling back to '${defaultLocale}'`);
            locale.set(defaultLocale);
            t.set(translations[defaultLocale]);
        }
    } catch (error) {
        console.error("Failed to load settings for i18n:", error);
        // Fallback to default on error
        locale.set(defaultLocale);
        t.set(translations[defaultLocale]);
    }
}

// Function to change the language
export function setLocale(lang) {
    if (translations[lang]) {
        locale.set(lang);
        t.set(translations[lang]);
    } else {
        console.warn(`Attempted to set unknown locale: ${lang}`);
    }
}
