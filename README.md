# VortECIO - Notebook Fan Control

[🇺🇦 Українська](#ukrainian) | [🇬🇧 English](#english)

---

<a name="ukrainian"></a>
## 🇺🇦 Українська версія

### 📋 Опис програми

**VortECIO** — це сучасна, легка та потужна утиліта для керування системою охолодження ноутбуків. Вона створена як сучасна альтернатива класичному NoteBook FanControl (NBFC), забезпечуючи повну сумісність з його конфігураційними файлами, але з використанням новітніх технологій інтерфейсу та моніторингу.

Програма дозволяє користувачам взяти під повний контроль швидкість обертання вентиляторів, щоб досягти ідеального балансу між тишею та продуктивністю системи.

### ✨ Ключові можливості та переваги

* **Сумісність з NBFC:** Повна підтримка файлів конфігурації `.xml` від NoteBook FanControl. Ви можете використовувати вже існуючі профілі для сотень моделей ноутбуків.
* **Точний моніторинг (LHM):** Інтеграція з **LibreHardwareMonitor** забезпечує миттєве та точне зчитування температури процесора (включно з температурою ядер) та відеокарти, що є значно надійнішим за стандартні методи WMI.
* **Гнучкі режими керування:**
    * **Automatic:** Плавне регулювання швидкості вентиляторів на основі кривої температур, визначеної у конфігурації.
    * **Manual:** Ручне встановлення фіксованої швидкості за допомогою зручного повзунка.
    * **Read-only:** Режим моніторингу, що дозволяє спостерігати за показниками без втручання в роботу системи.
    * **Disabled:** Повне вимкнення керування (повернення до заводських налаштувань BIOS/EC).
* **Сучасний інтерфейс:** Стильний GUI, написаний на `customtkinter`, з підтримкою **Темної** та **Світлої** тем, що гармонійно виглядає в Windows 10/11.
* **Робота в фоні:** Підтримка згортання в системний трей (System Tray) та автоматичний запуск разом з Windows.
* **Мультимовність:** Інтерфейс перекладено багатьма мовами: Українська, Англійська, Німецька, Польська, Японська.

### 🛡️ Безпека

VortECIO має вбудовану систему захисту. Якщо програма втрачає зв'язок із температурними сенсорами, вона автоматично переходить у безпечний режим, повертаючи керування вентиляторами системі (BIOS), щоб уникнути перегріву.

### 🧩 Архітектура

Програма використовує модульну архітектуру плагінів. Основний модуль сенсорів (`lhm_sensor`) працює ізольовано, що забезпечує стабільність основної програми. Взаємодія з Embedded Controller (EC) ноутбука здійснюється через перевірений часом драйвер `InpOutx64`.

### 🤝 Подяки та Кредити

Цей проєкт став можливим завдяки чудовим інструментам та спільноті Open Source:

* **NoteBook FanControl (NBFC):** За натхнення, стандартизацію конфігураційних файлів та дослідження в області керування EC.
* **LibreHardwareMonitor:** За чудову бібліотеку моніторингу апаратного забезпечення.
* **CustomTkinter:** За можливість створення сучасного та естетичного інтерфейсу користувача.
* **Highresolution Enterprises:** За драйвер `InpOut32/x64`, що дозволяє прямий доступ до апаратних портів.
* **Icon8:** За графічні ресурси (іконки).

---

<a name="english"></a>
## 🇬🇧 English Version

### 📋 Description

**VortECIO** is a modern, lightweight, and powerful utility for laptop cooling system control. Designed as a contemporary alternative to the classic NoteBook FanControl (NBFC), it maintains full compatibility with NBFC configuration files while leveraging modern UI technologies and monitoring methods.

The application allows users to take full control of fan speeds, achieving the perfect balance between silence and system performance.

### ✨ Key Features & Advantages

* **NBFC Compatibility:** Full support for NoteBook FanControl `.xml` configuration files. You can use existing profiles created for hundreds of laptop models.
  - **Extended XML Support:** VortECIO now supports additional NBFC tags like `<CriticalTemperature>` for model-specific thermal shutdown and `<EcIoPorts>` for laptops with non-standard Embedded Controller addresses.
* **Precise Monitoring (LHM):** Integration with **LibreHardwareMonitor** ensures instant and accurate reading of CPU (including per-core) and GPU temperatures, offering significantly higher reliability than standard WMI methods.
* **Flexible Control Modes:**
    * **Automatic:** Smooth fan speed adjustment based on the temperature curve defined in the configuration.
    * **Manual:** Set a fixed speed manually using a convenient slider.
    * **Read-only:** Monitoring mode that allows observing metrics without interfering with system operation.
    * **Disabled:** Completely disables control (reverts to factory BIOS/EC settings).
* **Modern UI:** Stylish GUI built with `customtkinter`, supporting both **Dark** and **Light** themes, blending perfectly with Windows 10/11.
* **Background Operation:** Supports minimizing to the System Tray and automatically starting with Windows.
* **Multi-language Support:** The interface is translated into multiple languages: English, Ukrainian, German, Polish, Japanese.

### 🛡️ Safety

VortECIO features a built-in safety system. If the application loses connection with temperature sensors, it automatically triggers a failsafe mode, returning fan control to the system (BIOS) to prevent overheating.

### 🧩 Architecture

The program utilizes a modular plugin architecture. The primary sensor module (`lhm_sensor`) operates in isolation, ensuring the stability of the main application. Interaction with the laptop's Embedded Controller (EC) is handled via the time-tested `InpOutx64` driver.

### 🤝 Acknowledgments & Credits

This project was made possible thanks to amazing tools and the Open Source community:

* **NoteBook FanControl (NBFC):** For inspiration, standardization of configuration files, and research into EC control.
* **LibreHardwareMonitor:** For the excellent hardware monitoring library.
* **CustomTkinter:** For enabling the creation of a modern and aesthetic user interface.
* **Highresolution Enterprises:** For the `InpOut32/x64` driver, enabling direct hardware port access.
* **Icon8:** For graphical resources (icons).
