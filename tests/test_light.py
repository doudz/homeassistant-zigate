"""Test zigate light."""
import unittest


class TestLight(unittest.TestCase):
    def test_light(self):
        from custom_components.zigate import light  # noqa


if __name__ == '__main__':
    unittest.main()
