"""Test zigate sensor."""
import unittest

from homeassistant.components.sensor import DOMAIN

class TestSensor(unittest.TestCase):
    def test_sensor(self):
        from zigate import sensor
    
    
if __name__ == '__main__':
    unittest.main()