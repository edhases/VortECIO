# VortECIO - Notebook Fan Control

[🇺🇦 Українська](#ukrainian) | [🇬🇧 English](#english)

---

<a name="ukrainian"></a>
## 🇺🇦 Українська версія

### 📋 Опис

**VortECIO** - це сучасна альтернатива NoteBook FanControl (NBFC), написана на Python. Програма забезпечує автоматичне та ручне керування вентиляторами ноутбука з підтримкою NBFC конфігурацій.

### ✨ Особливості

- 🌡️ **Точний моніторинг температури** через LibreHardwareMonitor
- 🔧 **Повна сумісність з NBFC конфігураціями** (XML формат)
- 🎛️ **Гнучке керування** - автоматичний та ручний режими
- 🔌 **Система плагінів** для розширення функціоналу
- 📊 **Графік температури** в реальному часі
- 🌍 **Багатомовність** (Українська, English, Deutsch, Polski, 日本語)
- 🎨 **Теми оформлення** (Light, Dark, Black)
- 💾 **System Tray** підтримка
- 📝 **Детальне логування** для дебагу

### 📦 Вимоги

**Системні вимоги:**
- Windows 10/11 (64-bit)
- Права адміністратора (для доступу до EC регістрів)
- .NET Framework 4.7.2+ (для LibreHardwareMonitor)

**Python залежності:**
Python 3.8+
pythonnet >= 3.0.0
pystray >= 0.19.4
pillow >= 9.0.0

text

### 🚀 Встановлення

#### 1. Клонування репозиторію
git clone https://github.com/yourusername/VortECIO.git
cd VortECIO

text

#### 2. Встановлення залежностей
pip install -r requirements.txt

text

#### 3. Налаштування LibreHardwareMonitor

**Завантажити:**
- Перейдіть на https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases
- Завантажте останню версію
- Розпакуйте `LibreHardwareMonitorLib.dll`

**Розмістити:**
Скопіюйте DLL в папку плагіну
copy LibreHardwareMonitorLib.dll plugins\lhm_sensor\

text

#### 4. Перевірка встановлення
python test_lhm.py

text

Якщо всі тести пройдені ✅ - можна запускати програму!

### 🎮 Використання

#### Запуск програми
Стандартний запуск (з GUI)
python main.py

Запуск у system tray
python main.py --start-in-tray

text

#### Перший запуск

1. **Завантажити конфігурацію:**
   - `File → Load Config`
   - Виберіть XML конфігурацію для вашого ноутбука

2. **Налаштувати режим вентиляторів:**
   - **Auto** - автоматичне керування по температурі
   - **Manual** - ручне встановлення швидкості (%)
   - **Read-only** - тільки моніторинг
   - **Disabled** - вимкнено

3. **Увімкнути плагіни:**
   - `Settings → Plugins → Manage Plugins`
   - Увімкніть `lhm_sensor` (рекомендовано)

### 📁 Структура проєкту

VortECIO/
├── main.py # Головний файл
├── logger.py # Система логування
├── config.py # Конфігурація
├── hardware.py # EC драйвер (InpOutx64)
├── fan_controller.py # Логіка контролю вентиляторів
├── plugin_manager.py # Менеджер плагінів
├── requirements.txt # Python залежності
├── inpoutx64.dll # Драйвер для EC доступу
│
├── ui/ # Інтерфейс
│ ├── main_window.py # Головне вікно
│ ├── temperature_graph.py # Графік температури
│ └── plugin_manager_window.py
│
├── plugins/ # Плагіни
│ └── lhm_sensor/ # LibreHardwareMonitor сенсор
│ ├── init.py
│ ├── LibreHardwareMonitorLib.dll
│ └── README.md
│
├── logs/ # Логи (автоматично)
└── configs/ # NBFC конфігурації (опціонально)

text

### 🔌 Плагіни

#### LibreHardwareMonitor Sensor (lhm_sensor)

**Основний плагін** для моніторингу температури та RPM вентиляторів.

**Можливості:**
- Температура CPU (per-core та package)
- Температура GPU (NVIDIA/AMD/Intel)
- Обороти вентиляторів (RPM)
- Напруга та інші метрики

**Увімкнення:**
1. `Settings → Plugins → Manage Plugins`
2. Поставте галочку біля `lhm_sensor`
3. Перезапустіть програму

#### Створення власних плагінів

plugins/my_sensor/init.py
from logger import get_logger

logger = get_logger('MySensor')

class MySensor:
def get_temperature(self):
# Ваша логіка читання температури
return 45.0

def register(app_logic):
sensor = MySensor()
app_logic.register_sensor(sensor)
logger.info("MySensor registered")
return sensor

text

### 🛠️ Конфігурація

#### NBFC XML конфігурації

VortECIO підтримує стандартні NBFC конфігурації:

<?xml version="1.0"?> <FanControlConfigV2> <NotebookModel>HP Pavilion Gaming 15</NotebookModel> <Author>Your Name</Author> <EcPollInterval>1000</EcPollInterval> <FanConfigurations> <FanConfiguration> <ReadRegister>47</ReadRegister> <WriteRegister>45</WriteRegister> <MinSpeedValue>0</MinSpeedValue> <MaxSpeedValue>100</MaxSpeedValue> <FanDisplayName>CPU</FanDisplayName>
text
  <TemperatureThresholds>
    <TemperatureThreshold>
      <UpThreshold>60</UpThreshold>
      <DownThreshold>0</DownThreshold>
      <FanSpeed>0</FanSpeed>
    </TemperatureThreshold>
    <!-- Додаткові пороги... -->
  </TemperatureThresholds>
</FanConfiguration>
</FanConfigurations> </FanControlConfigV2> ```
settings.json
Користувацькі налаштування зберігаються автоматично:

text
{
    "last_config_path": "configs/my_laptop.xml",
    "theme": "dark",
    "language": "uk",
    "autostart": true,
    "active_plugins": ["lhm_sensor"]
}
