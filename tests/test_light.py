"""Test zigate light."""
import unittest

from homeassistant.components.light import DOMAIN

class TestLight(unittest.TestCase):
    def test_light(self):
        from zigate import light
    
    
if __name__ == '__main__':
    unittest.main()