# LibreHardwareMonitor Sensor Plugin

## Встановлення

1. Встановити pythonnet:
```
pip install pythonnet
```

2. Завантажити LibreHardwareMonitorLib.dll:
   - https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases
   - Розпакувати `LibreHardwareMonitorLib.dll`
   - Помістити у `plugins/lhm_sensor/`

3. Увімкнути плагін у Settings -> Manage Plugins

## Troubleshooting

Якщо DLL не завантажується, перевірте:
- .NET Framework 4.7.2+ встановлений
- DLL не заблокована Windows (Properties -> Unblock)
- Програма запущена з правами адміністратора
