"""Test zigate cover."""
import unittest


class TestCover(unittest.TestCase):
    def test_cover(self):
        from custom_components.zigate import cover  # noqa


if __name__ == '__main__':
    unittest.main()
