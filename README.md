# VortECIO-Go

![VortECIO-Go Screenshot](https://i.imgur.com/8V5Z8Q3.png)

**VortECIO-Go** — це сучасна утиліта для керування вентиляторами ноутбуків під Windows, розроблена як альтернатива NoteBook FanControl (NBFC). Проєкт написаний на Go та Svelte (через Wails v2) і націлений на створення єдиного, легко розповсюджуваного `.exe` файлу без залежностей.

Цей інструмент дозволяє користувачам точно налаштовувати швидкість обертання вентиляторів залежно від температури процесора (CPU) та відеокарти (GPU), використовуючи оригінальні XML-конфігурації від спільноти NBFC.

---

## 🇺🇦 Українська Версія

### Ключові Особливості

- **Сумісність з NBFC:** Нативна підтримка понад 260 XML-файлів конфігурацій від NoteBook FanControl.
- **Низькорівневий Контроль:** Прямий доступ до Embedded Controller (EC) через `inpoutx64.dll` для миттєвого керування швидкістю.
- **Розумні Криві Вентиляторів:** Повністю налаштовувані криві швидкості, що дозволяють створити ідеальний баланс між продуктивністю та тишею.
- **Безпека:** Вбудований "watchdog", що повертає керування BIOS у разі збою програми або зависання сенсорів, а також механізм захисту від критичного перегріву.
- **Плавне Регулювання:** Підтримка гістерезису та плавного кроку (smoothing) для уникнення різких стрибків обертів.
- **Моніторинг у Режимі Реального Часу:** Відображення температури CPU/GPU та поточної швидкості вентиляторів у відсотках та RPM.
- **Сучасний UI:** Інтуїтивно зрозумілий інтерфейс, створений на Svelte, з інтерактивним графіком для редагування кривих.
- **Багатомовність:** Підтримка української, англійської, німецької, польської та японської мов.
- **Робота в Треї:** Можливість згорнути програму в системний трей з відображенням поточної температури.

### Встановлення та Запуск

1.  **Завантажте останній реліз** з [секції Releases](https://github.com/your-repo/VortECIO-Go/releases) на GitHub.
2.  Розпакуйте архів.
3.  Запустіть `VortECIO-Go.exe`.

**Вимоги:**
*   Windows 10/11 (x64).
*   Права адміністратора для першого запуску (для встановлення драйвера `inpoutx64.dll`).

### Як Користуватися

1.  **Завантажити Конфігурацію:**
    *   Після першого запуску програма запропонує завантажити конфігураційний файл.
    *   Виберіть XML-файл, що відповідає вашій моделі ноутбука, з папки `Configs` (яка постачається з архівом) або з онлайн-репозиторію NBFC.
2.  **Налаштувати Криву (Режим "Auto"):**
    *   На головному екрані ви побачите графік залежності швидкості вентилятора від температури.
    *   Перетягуйте точки на графіку, щоб налаштувати бажану швидкість для різних температурних порогів.
    *   Зміни застосовуються миттєво.
3.  **Ручне Керування (Режим "Manual"):**
    *   Перемкніть режим на "Manual" та використовуйте слайдер для встановлення фіксованої швидкості.
4.  **Зберегти Налаштування:**
    *   Усі зміни, включаючи положення точок на графіку, зберігаються автоматично у файл `user_profiles.json` у теці з програмою.

### Розробка

Якщо ви бажаєте зробити внесок у проєкт:

1.  Встановіть [Go](https://golang.org/) (версія 1.21+).
2.  Встановіть [Wails v2](https://wails.io/docs/gettingstarted/installation).
3.  Встановіть [Node.js](https://nodejs.org/) та `npm`.
4.  Клонуйте репозиторій:
    ```bash
    git clone https://github.com/your-repo/VortECIO-Go.git
    cd VortECIO-Go
    ```
5.  Встановіть залежності фронтенду:
    ```bash
    wails npm install
    ```
6.  Запустіть у режимі розробки:
    ```bash
    wails dev
    ```
7.  Для збірки фінального `.exe`:
    ```bash
    wails build
    ```

---

## 🇬🇧 English Version

### Key Features

- **NBFC Compatibility:** Native support for over 260 XML configuration files from NoteBook FanControl.
- **Low-Level Control:** Direct access to the Embedded Controller (EC) via `inpoutx64.dll` for instant speed management.
- **Smart Fan Curves:** Fully customizable fan curves, allowing you to create the perfect balance between performance and silence.
- **Safety:** A built-in "watchdog" that returns control to the BIOS in case of a program crash or sensor freeze, along with a critical temperature protection mechanism.
- **Smooth Adjustments:** Hysteresis and smoothing support to prevent abrupt RPM jumps.
- **Real-Time Monitoring:** Displays CPU/GPU temperature and current fan speed in both percentage and RPM.
- **Modern UI:** An intuitive interface built with Svelte, featuring an interactive chart for editing fan curves.
- **Multilingual:** Supports English, Ukrainian, German, Polish, and Japanese.
- **System Tray Operation:** The application can be minimized to the system tray, displaying the current temperature.

### Installation and Usage

1.  **Download the latest release** from the [Releases section](https://github.com/your-repo/VortECIO-Go/releases) on GitHub.
2.  Unpack the archive.
3.  Run `VortECIO-Go.exe`.

**Requirements:**
*   Windows 10/11 (x64).
*   Administrator rights for the first launch (to install the `inpoutx64.dll` driver).

### How to Use

1.  **Load Configuration:**
    *   On the first launch, the program will prompt you to load a configuration file.
    *   Select the XML file corresponding to your notebook model from the `Configs` folder (included in the archive) or from the online NBFC repository.
2.  **Adjust the Fan Curve ("Auto" Mode):**
    *   On the main screen, you will see a graph showing the fan speed's dependency on temperature.
    *   Drag the points on the graph to set the desired speed for different temperature thresholds.
    *   Changes are applied instantly.
3.  **Manual Control ("Manual" Mode):**
    *   Switch to "Manual" mode and use the slider to set a fixed speed.
4.  **Save Settings:**
    *   All changes, including the positions of the points on the graph, are automatically saved to a `user_profiles.json` file in the application's directory.

### Development

If you wish to contribute to the project:

1.  Install [Go](https://golang.org/) (version 1.21+).
2.  Install [Wails v2](https://wails.io/docs/gettingstarted/installation).
3.  Install [Node.js](https://nodejs.org/) and `npm`.
4.  Clone the repository:
    ```bash
    git clone https://github.com/your-repo/VortECIO-Go.git
    cd VortECIO-Go
    ```
5.  Install frontend dependencies:
    ```bash
    wails npm install
    ```
6.  Run in development mode:
    ```bash
    wails dev
    ```
7.  To build the final `.exe`:
    ```bash
    wails build
    ```
