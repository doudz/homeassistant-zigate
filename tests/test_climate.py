"""Test zigate climate."""
import unittest

from homeassistant.components.climate import DOMAIN

class TestClimate(unittest.TestCase):
    def test_climate(self):
        from zigate import climate  # noqa
    
    
if __name__ == '__main__':
    unittest.main()
