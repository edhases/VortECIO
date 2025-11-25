import mmap
import struct

class HwInfoSensor:
    def __init__(self):
        self.shm_name = r"Global\HWiNFO_SENS_SM2"

    def get_temperature(self):
        try:
            # Це спрощений приклад. HWiNFO SDK вимагає парсингу структури,
            # але для демонстрації ми просто повертаємо заглушку,
            # яка показує, що плагін активний.
            # У реальності тут буде код читання Shared Memory.

            # shm = mmap.mmap(0, 0x2000, self.shm_name, access=mmap.ACCESS_READ)
            # ... логіка пошуку Tctl/Tdie ...
            # shm.close()

            return 0.0 # Поки що повернемо 0 або реальне значення, якщо реалізуєш парсер
        except:
            return 0.0

def register(app_logic):
    sensor = HwInfoSensor()
    # Реєструємо цей сенсор як головний у додатку
    app_logic.register_sensor(sensor)
    return sensor
