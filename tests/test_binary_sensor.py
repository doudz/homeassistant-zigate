"""Test zigate binary sensor."""
import unittest


class TestBinarySensor(unittest.TestCase):
    def test_binary_sensor(self):
        from custom_components.zigate import binary_sensor  # noqa


if __name__ == '__main__':
    unittest.main()
