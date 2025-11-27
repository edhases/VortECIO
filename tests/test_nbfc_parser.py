import unittest
import tempfile
import os
from main import NbfcConfigParser

class TestNbfcParser(unittest.TestCase):
    def test_parse_critical_temperature(self):
        """Test parsing CriticalTemperature from XML"""
        xml_content = """<?xml version="1.0"?>
        <FanControlConfigV2>
            <NotebookModel>Test Laptop</NotebookModel>
            <CriticalTemperature>85</CriticalTemperature>
            <EcPollInterval>1000</EcPollInterval>
        </FanControlConfigV2>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name

        try:
            parser = NbfcConfigParser(temp_path)
            self.assertTrue(parser.parse())
            self.assertEqual(parser.critical_temperature, 85)
        finally:
            os.unlink(temp_path)

    def test_parse_custom_ec_ports(self):
        """Test parsing custom EC I/O ports"""
        xml_content = """<?xml version="1.0"?>
        <FanControlConfigV2>
            <NotebookModel>ASUS Special</NotebookModel>
            <EcIoPorts>
                <DataPort>0x60</DataPort>
                <CommandPort>0x64</CommandPort>
            </EcIoPorts>
        </FanControlConfigV2>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name

        try:
            parser = NbfcConfigParser(temp_path)
            self.assertTrue(parser.parse())
            self.assertEqual(parser.ec_data_port, 0x60)
            self.assertEqual(parser.ec_command_port, 0x64)
        finally:
            os.unlink(temp_path)

    def test_detect_inverted_range(self):
        """Test auto-detection of inverted fan speed ranges"""
        xml_content = """<?xml version="1.0"?>
        <FanControlConfigV2>
            <NotebookModel>Acer VN7</NotebookModel>
            <FanConfigurations>
                <FanConfiguration>
                    <FanDisplayName>Test Fan</FanDisplayName>
                    <ReadRegister>149</ReadRegister>
                    <WriteRegister>148</WriteRegister>
                    <MinSpeedValue>255</MinSpeedValue>
                    <MaxSpeedValue>74</MaxSpeedValue>
                    <FanSpeedResetValue>255</FanSpeedResetValue>
                </FanConfiguration>
            </FanConfigurations>
        </FanControlConfigV2>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name

        try:
            parser = NbfcConfigParser(temp_path)
            self.assertTrue(parser.parse())
            self.assertEqual(len(parser.fans), 1)
            self.assertTrue(parser.fans[0]['is_inverted'])
        finally:
            os.unlink(temp_path)

if __name__ == '__main__':
    unittest.main()
