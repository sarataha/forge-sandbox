import unittest

from sandbox.__main__ import greet


class GreetTest(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("ada"), "hello, ada")


if __name__ == "__main__":
    unittest.main()
