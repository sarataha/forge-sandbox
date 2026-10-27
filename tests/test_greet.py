import io
import unittest
from contextlib import redirect_stdout

from sandbox.__main__ import greet, main


class GreetTest(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("ada"), "hello, ada")

    def test_greet_shout(self):
        self.assertEqual(greet("ada", shout=True), "HELLO, ADA")

    def test_cli_shout_flag(self):
        for argv, want in ((["greet", "ada", "--shout"], "HELLO, ADA\n"), (["greet", "ada"], "hello, ada\n")):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(main(argv), 0)
            self.assertEqual(buf.getvalue(), want)


if __name__ == "__main__":
    unittest.main()
