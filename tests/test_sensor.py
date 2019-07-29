"""Test zigate sensor."""
import unittest


class TestSensor(unittest.TestCase):
    def test_sensor(self):
        from custom_components.zigate import sensor  # noqa


if __name__ == '__main__':
    unittest.main()
