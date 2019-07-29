"""Test zigate climate."""
import unittest


class TestClimate(unittest.TestCase):
    def test_climate(self):
        from custom_components.zigate import climate  # noqa


if __name__ == '__main__':
    unittest.main()
