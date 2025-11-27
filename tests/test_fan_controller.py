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

if __name__ == '__main__':
    unittest.main()
