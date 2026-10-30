import importlib
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from sandbox.__main__ import main


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class NotesCliBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "n.json")
        patcher = mock.patch.dict(os.environ, {"SANDBOX_NOTES_FILE": self.path})
        patcher.start()
        self.addCleanup(patcher.stop)

    def read_bytes(self):
        with open(self.path, "rb") as f:
            return f.read()


class AddTest(NotesCliBase):
    def test_add_on_missing_file_prints_added_1(self):
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(run_cli("notes", "add", "buy milk"), (0, "added 1\n", ""))
        self.assertTrue(os.path.exists(self.path))

    def test_second_add_prints_added_2(self):
        run_cli("notes", "add", "buy milk")
        self.assertEqual(run_cli("notes", "add", "walk dog"), (0, "added 2\n", ""))

    def test_add_strips_surrounding_whitespace(self):
        run_cli("notes", "add", "  buy milk \t")
        self.assertEqual(run_cli("notes", "list"), (0, "1\tbuy milk\n", ""))

    def test_add_accepts_exactly_200_chars(self):
        text = "x" * 200
        self.assertEqual(run_cli("notes", "add", text), (0, "added 1\n", ""))
        self.assertEqual(run_cli("notes", "list"), (0, "1\t" + text + "\n", ""))


class ListTest(NotesCliBase):
    def test_list_prints_id_tab_text_in_id_order(self):
        run_cli("notes", "add", "buy milk")
        run_cli("notes", "add", "walk dog")
        run_cli("notes", "add", "call mum")
        self.assertEqual(
            run_cli("notes", "list"),
            (0, "1\tbuy milk\n2\twalk dog\n3\tcall mum\n", ""),
        )

    def test_list_missing_file_prints_nothing_exit_0(self):
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(run_cli("notes", "list"), (0, "", ""))
        self.assertFalse(os.path.exists(self.path))

    def test_list_zero_byte_file_prints_nothing_exit_0(self):
        with open(self.path, "w"):
            pass
        self.assertEqual(run_cli("notes", "list"), (0, "", ""))

    def test_list_file_with_no_notes_prints_nothing_exit_0(self):
        with open(self.path, "w") as f:
            f.write('{"notes": []}')
        self.assertEqual(run_cli("notes", "list"), (0, "", ""))

    def test_add_after_zero_byte_file_prints_added_1(self):
        with open(self.path, "w"):
            pass
        self.assertEqual(run_cli("notes", "add", "buy milk"), (0, "added 1\n", ""))


class AddRejectsBadTextTest(NotesCliBase):
    def assert_rejected(self, text):
        code, out, err = run_cli("notes", "add", text)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("notes: error: "), err)
        self.assertTrue(len(err) > len("notes: error: \n"), err)
        self.assertEqual(err.count("\n"), 1)
        self.assertTrue(err.endswith("\n"))

    def test_bad_text_on_missing_file_leaves_no_file(self):
        for text in ("", "   ", "\t\n ", "x" * 201, "a\tb", "a\nb"):
            with self.subTest(text=text):
                self.assert_rejected(text)
                self.assertFalse(os.path.exists(self.path))

    def test_bad_text_leaves_existing_file_unchanged(self):
        self.assertEqual(run_cli("notes", "add", "buy milk")[0], 0)
        before = self.read_bytes()
        for text in ("", "   ", "x" * 201, "a\tb", "a\nb", "a\r\nb"):
            with self.subTest(text=text):
                self.assert_rejected(text)
                self.assertEqual(self.read_bytes(), before)
        self.assertEqual(run_cli("notes", "list"), (0, "1\tbuy milk\n", ""))

    def test_tab_or_newline_inside_text_is_rejected(self):
        self.assertEqual(run_cli("notes", "add", "buy milk")[0], 0)
        before = self.read_bytes()
        for text in ("buy\tmilk", "buy\nmilk", "\tbuy milk\tand eggs"):
            with self.subTest(text=text):
                self.assert_rejected(text)
                self.assertEqual(self.read_bytes(), before)


class DiscoveryTest(NotesCliBase):
    def test_new_command_module_becomes_subcommand(self):
        from sandbox.notes import commands

        with tempfile.TemporaryDirectory() as extra:
            with open(os.path.join(extra, "hello.py"), "w") as f:
                f.write(
                    "def register(sub):\n"
                    "    sub.add_parser('hello')\n"
                    "\n"
                    "def run(args):\n"
                    "    print('hello from notes')\n"
                    "    return 0\n"
                )
            orig_path = list(commands.__path__)
            commands.__path__.append(extra)
            self.addCleanup(lambda: setattr(commands, "__path__", orig_path))
            self.addCleanup(sys.modules.pop, "sandbox.notes.commands.hello", None)
            importlib.invalidate_caches()
            self.assertEqual(run_cli("notes", "hello"), (0, "hello from notes\n", ""))

    def test_add_and_list_are_discovered_subcommands(self):
        self.assertEqual(run_cli("notes", "add", "a")[0], 0)
        self.assertEqual(run_cli("notes", "list")[0], 0)


class ExistingCommandsTest(unittest.TestCase):
    def test_greet_still_works(self):
        self.assertEqual(run_cli("greet", "ada"), (0, "hello, ada\n", ""))
        self.assertEqual(run_cli("greet", "ada", "--shout"), (0, "HELLO, ADA\n", ""))

    def test_ledger_still_registered(self):
        code, _, _ = run_cli("ledger", "--help")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
