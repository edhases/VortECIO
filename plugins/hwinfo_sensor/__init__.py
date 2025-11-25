import mmap
import struct

class HwInfoSensor:
    def __init__(self):
        self.shm_name = r"Global\HWiNFO_SENS_SM2"

    def get_temperature(self):
        try:
            # This is a simplified example. HWiNFO SDK requires parsing a structure,
            # but for demonstration purposes, we just return a stub value
            # that shows the plugin is active.
            # In a real implementation, this would involve reading from Shared Memory.

            # shm = mmap.mmap(0, 0x2000, self.shm_name, access=mmap.ACCESS_READ)
            # ... logic to find Tctl/Tdie ...
            # shm.close()

            # For demonstration, returning a fixed value.
            # To trigger panic mode, this should return None on failure.
            return 42.0
        except FileNotFoundError:
            # HWiNFO is not running or Shared Memory is not available
            return None
        except Exception:
            # Other potential errors during memory reading or parsing
            return None

def register(app_logic):
    sensor = HwInfoSensor()
    app_logic.register_sensor(sensor)
    return sensor
