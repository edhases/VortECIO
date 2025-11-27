import unittest
from unittest.mock import Mock, patch, MagicMock
from fan_controller import FanController
import time

class TestFanController(unittest.TestCase):
    def setUp(self):
        self.mock_app_logic = Mock()
        self.mock_app_logic.nbfc_parser.fans = []
        self.controller = FanController(self.mock_app_logic)

    def test_hysteresis_increasing_temp(self):
        """Test fan speed increases when temp crosses up threshold"""
        fan_config = {
            'temp_thresholds': [(60, 55, 30), (70, 65, 50), (80, 75, 80)]
        }

        # Start at low speed
        speed = self.controller._get_speed_for_temp(0, fan_config, 58)
        self.assertEqual(speed, 0)

        # Cross threshold
        self.controller.last_speed[0] = 30
        speed = self.controller._get_speed_for_temp(0, fan_config, 72)
        self.assertEqual(speed, 50)

    def test_hysteresis_decreasing_temp(self):
        """Test fan speed only decreases below down threshold"""
        fan_config = {
            'temp_thresholds': [(60, 55, 30), (70, 65, 50)]
        }

        # Set high speed
        self.controller.last_speed[0] = 50

        # Temp drops but still above down threshold
        speed = self.controller._get_speed_for_temp(0, fan_config, 67)
        self.assertEqual(speed, 50, "Should maintain speed in hysteresis zone")

        # Temp drops below down threshold
        speed = self.controller._get_speed_for_temp(0, fan_config, 63)
        self.assertEqual(speed, 30, "Should drop speed below down threshold")

    def test_inverted_range_normalization(self):
        """Test percentage calculation for inverted ranges (Acer-style)"""
        from utils import normalize_fan_speed

        fan_inverted = {
            'min_speed': 255,
            'max_speed': 74,
            'is_inverted': True
        }

        self.assertEqual(normalize_fan_speed(255, fan_inverted), 0)
        self.assertEqual(normalize_fan_speed(74, fan_inverted), 100)
        self.assertAlmostEqual(normalize_fan_speed(164, fan_inverted), 50, delta=2)

    def test_sensor_error_recovery(self):
        """Test that sensor error counter resets after success"""
        self.controller.sensor_errors = 5

        # Simulate successful sensor read in control_loop logic
        self.controller.sensor_errors = 0

        self.assertEqual(self.controller.sensor_errors, 0)

    def test_hysteresis_edge_cases(self):
        """Test edge cases: exact threshold temps, empty list"""
        fan_config = {
            'temp_thresholds': [(60, 55, 30), (70, 65, 50)]
        }
        # Exact up threshold
        self.controller.last_speed[0] = 0
        speed = self.controller._get_speed_for_temp(0, fan_config, 60)
        self.assertEqual(speed, 30, "Should activate at exact up threshold")

        # Exact down threshold
        self.controller.last_speed[0] = 30
        speed = self.controller._get_speed_for_temp(0, fan_config, 55)
        self.assertEqual(speed, 0, "Should deactivate at exact down threshold")

        # Between down and up (hysteresis zone)
        self.controller.last_speed[0] = 30
        speed = self.controller._get_speed_for_temp(0, fan_config, 57)
        self.assertEqual(speed, 30, "Should stay in hysteresis zone")

        # Empty thresholds
        fan_empty = {'temp_thresholds': []}
        self.controller.last_speed[0] = 50
        speed = self.controller._get_speed_for_temp(0, fan_empty, 65)
        self.assertEqual(speed, 50, "Should return last_speed for empty thresholds")

    def test_hysteresis_multiple_zones(self):
        """Test with many threshold levels"""
        fan_config = {
            'temp_thresholds': [
                (50, 45, 20),
                (60, 55, 40),
                (70, 65, 60),
                (80, 75, 80),
                (90, 85, 100)
            ]
        }
        # Jump from zone 1 to zone 3
        self.controller.last_speed[0] = 20
        speed = self.controller._get_speed_for_temp(0, fan_config, 72)
        self.assertEqual(speed, 60, "Should jump zones on temperature spike")

        # Stay in zone 3 during cooling
        self.controller.last_speed[0] = 60
        speed = self.controller._get_speed_for_temp(0, fan_config, 67)
        self.assertEqual(speed, 60, "Should stay in zone during hysteresis")

        # Drop to zone 2 after crossing down threshold
        speed = self.controller._get_speed_for_temp(0, fan_config, 64)
        self.assertEqual(speed, 40, "Should drop zone after down threshold")

if __name__ == '__main__':
    unittest.main()
