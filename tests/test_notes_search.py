import io
import os
import pathlib
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


class SearchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "n.json")
        patcher = mock.patch.dict(os.environ, {"SANDBOX_NOTES_FILE": self.path})
        patcher.start()
        self.addCleanup(patcher.stop)

    def add(self, *texts):
        for t in texts:
            run_cli("notes", "add", t)

    def test_match_prints_id_tab_text_exit_0(self):
        self.add("visit the bank", "buy milk")
        self.assertEqual(
            run_cli("notes", "search", "bank"), (0, "1\tvisit the bank\n", "")
        )

    def test_uppercase_word_matches_lowercase_text(self):
        self.add("visit the bank", "buy milk")
        self.assertEqual(
            run_cli("notes", "search", "BANK"), (0, "1\tvisit the bank\n", "")
        )

    def test_lowercase_word_matches_uppercase_text(self):
        self.add("Call BANK today")
        self.assertEqual(
            run_cli("notes", "search", "bank"), (0, "1\tCall BANK today\n", "")
        )

    def test_mixed_case_word_matches_mixed_case_text(self):
        self.add("river Bank walk", "buy milk")
        self.assertEqual(
            run_cli("notes", "search", "bAnK"), (0, "1\triver Bank walk\n", "")
        )

    def test_prints_every_match_in_id_order(self):
        self.add("bank holiday", "buy milk", "Bank transfer", "walk dog", "river bank")
        self.assertEqual(
            run_cli("notes", "search", "BANK"),
            (0, "1\tbank holiday\n3\tBank transfer\n5\triver bank\n", ""),
        )

    def test_matches_substring_inside_a_word(self):
        self.add("banking app", "buy milk")
        self.assertEqual(
            run_cli("notes", "search", "bank"), (0, "1\tbanking app\n", "")
        )

    def test_no_match_prints_nothing_exit_1(self):
        self.add("visit the bank", "buy milk")
        self.assertEqual(run_cli("notes", "search", "zebra"), (1, "", ""))

    def test_no_match_on_missing_file_exit_1(self):
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(run_cli("notes", "search", "zebra"), (1, "", ""))

    def _assert_bad_word(self, word):
        self.add("visit the bank")
        code, out, err = run_cli("notes", "search", word)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("notes: error: "), err)
        self.assertTrue(err.endswith("\n"))
        self.assertEqual(len(err.splitlines()), 1)
        self.assertGreater(len(err.strip()), len("notes: error:"))

    def test_empty_word_is_error_exit_2(self):
        self._assert_bad_word("")

    def test_whitespace_only_word_is_error_exit_2(self):
        self._assert_bad_word("   ")

    def test_tab_only_word_is_error_exit_2(self):
        self._assert_bad_word("\t")

    def test_error_on_empty_word_leaves_file_unchanged(self):
        self.add("visit the bank")
        with open(self.path, "rb") as f:
            before = f.read()
        run_cli("notes", "search", "  ")
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_search_found_by_discovery_cli_py_has_no_search_reference(self):
        cli_src = (
            pathlib.Path(__file__).resolve().parents[1] / "sandbox" / "notes" / "cli.py"
        )
        self.assertNotIn("search", cli_src.read_text())
        self.add("visit the bank")
        self.assertEqual(run_cli("notes", "search", "bank")[0], 0)


if __name__ == "__main__":
    unittest.main()
