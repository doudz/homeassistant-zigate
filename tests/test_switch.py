"""Test zigate switch."""
import unittest

from homeassistant.components.switch import DOMAIN

class TestSwitch(unittest.TestCase):
    def test_switch(self):
        from zigate import switch  # noqa
    
    
if __name__ == '__main__':
    unittest.main()
