import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from sandbox.notes import store
from tests.test_notes_add_list import NotesCliBase, run_cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _u(*cps):
    return "".join(chr(c) for c in cps)


GOOD = [
    "caf" + _u(0xE9) + " au lait",
    "party " + _u(0x1F389),
    "family " + _u(0x1F468, 0x200D, 0x1F469, 0x200D, 0x1F467),
    _u(
        0x645,
        0x631,
        0x62D,
        0x628,
        0x627,
        0x20,
        0x628,
        0x627,
        0x644,
        0x639,
        0x627,
        0x644,
        0x645,
    ),
    _u(0x5E9, 0x5DC, 0x5D5, 0x5DD),
]
BAD = {
    "esc": "a" + _u(0x1B) + "b",
    "bel": "a" + _u(0x07) + "b",
    "vt": "a" + _u(0x0B) + "b",
    "ff": "a" + _u(0x0C) + "b",
    "nel": "a" + _u(0x85) + "b",
    "ls": "a" + _u(0x2028) + "b",
    "ps": "a" + _u(0x2029) + "b",
    "rlo": "a" + _u(0x202E) + "b",
    "zwsp": "a" + _u(0x200B) + "b",
    "bom": "a" + _u(0xFEFF) + "b",
    "surrogate": "caf" + _u(0xDCE9),
    "private_use": "a" + _u(0xE000) + "b",
    "noncharacter": "a" + _u(0xFFFE) + "b",
    "noncharacter_fdd0": "a" + _u(0xFDD0) + "b",
}


def sandbox(*argv, env=None, stdin=None, **kw):
    full = dict(os.environ, **(env or {}))
    return subprocess.run(
        [sys.executable, "-m", "sandbox", *argv],
        cwd=ROOT,
        env=full,
        capture_output=True,
        check=False,
        **kw,
    )


class TextRuleTest(NotesCliBase):
    def test_valid_text_adds_lists_searches(self):
        for i, text in enumerate(GOOD, 1):
            with self.subTest(text=text):
                self.assertEqual(run_cli("notes", "add", text), (0, f"added {i}\n", ""))
        code, out, _ = run_cli("notes", "list")
        self.assertEqual(code, 0)
        self.assertEqual(out, "".join(f"{i}\t{t}\n" for i, t in enumerate(GOOD, 1)))
        self.assertEqual(run_cli("notes", "search", "CAFÉ"), (0, f"1\t{GOOD[0]}\n", ""))
        self.assertEqual(run_cli("notes", "search", "של")[0], 0)

    def test_bad_characters_rejected_file_untouched(self):
        for name, text in BAD.items():
            with self.subTest(case=name):
                code, out, err = run_cli("notes", "add", text)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("notes: error: "), err)
                self.assertEqual(len(err.splitlines()), 1, err)
                self.assertFalse(os.path.exists(self.path))

    def test_edge_whitespace_controls_are_stripped_not_rejected(self):
        self.assertEqual(run_cli("notes", "add", "\x0bhi\x0c"), (0, "added 1\n", ""))

    def test_stored_bad_text_is_unreadable(self):
        for name, text in BAD.items():
            data = json.dumps({"notes": [{"id": 1, "text": text}]}).encode("ascii")
            with open(self.path, "wb") as f:
                f.write(data)
            for argv in (
                ("notes", "list"),
                ("notes", "add", "x"),
                ("notes", "search", "a"),
            ):
                with self.subTest(case=name, argv=argv):
                    code, out, err = run_cli(*argv)
                    self.assertEqual((code, out), (2, ""))
                    self.assertTrue(err.startswith("notes: error: cannot read"), err)
                    self.assertEqual(len(err.splitlines()), 1, err)
                    self.assertEqual(self.read_bytes(), data)

    def test_stored_zwj_text_loads(self):
        run_cli("notes", "add", GOOD[2])
        self.assertEqual(store.load()[0]["text"], GOOD[2])

    def test_zero_byte_file_means_no_notes(self):
        open(self.path, "wb").close()
        self.assertEqual(run_cli("notes", "list"), (0, "", ""))
        self.assertEqual(run_cli("notes", "add", "x"), (0, "added 1\n", ""))

    def test_ids_below_one_are_unreadable(self):
        for bad_id in (0, -5):
            data = json.dumps({"notes": [{"id": bad_id, "text": "a"}]}).encode()
            with open(self.path, "wb") as f:
                f.write(data)
            for argv in (("notes", "list"), ("notes", "add", "x")):
                with self.subTest(id=bad_id, argv=argv):
                    code, out, err = run_cli(*argv)
                    self.assertEqual((code, out), (2, ""))
                    self.assertTrue(err.startswith("notes: error: cannot read"), err)
                    self.assertEqual(self.read_bytes(), data)

    def test_id_one_still_loads(self):
        with open(self.path, "w") as f:
            json.dump({"notes": [{"id": 1, "text": "a"}]}, f)
        self.assertEqual(run_cli("notes", "list"), (0, "1\ta\n", ""))


class WriteFailureTest(unittest.TestCase):
    def test_missing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nope", "n.json")
            with mock.patch.dict(os.environ, {"SANDBOX_NOTES_FILE": path}):
                code, out, err = run_cli("notes", "add", "x")
            self.assertEqual((code, out), (2, ""))
            self.assertTrue(err.startswith(f"notes: error: cannot write {path}: "), err)
            self.assertEqual(len(err.splitlines()), 1, err)
            self.assertNotIn(".tmp", err)

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs non-root posix")
    def test_read_only_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "n.json")
            os.chmod(tmp, 0o500)
            try:
                with mock.patch.dict(os.environ, {"SANDBOX_NOTES_FILE": path}):
                    code, out, err = run_cli("notes", "add", "x")
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(
                    err.startswith(f"notes: error: cannot write {path}: "), err
                )
                self.assertEqual(len(err.splitlines()), 1, err)
                self.assertEqual(os.listdir(tmp), [])
            finally:
                os.chmod(tmp, 0o700)

    def test_replace_failure_cleans_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "n.json")
            with (
                mock.patch.dict(os.environ, {"SANDBOX_NOTES_FILE": path}),
                mock.patch("os.replace", side_effect=OSError(28, "No space left")),
            ):
                code, _out, err = run_cli("notes", "add", "x")
            self.assertEqual(code, 2)
            self.assertIn("cannot write", err)
            self.assertIn("No space left", err)
            self.assertEqual(os.listdir(tmp), [])


class ProcessTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "n.json")
        self.env = {"SANDBOX_NOTES_FILE": self.path}

    def test_invalid_utf8_argument_rejected(self):
        r = subprocess.run(
            [sys.executable, "-m", "sandbox", "notes", "add", b"caf\xe9"],
            cwd=ROOT,
            env=dict(os.environ, **self.env),
            capture_output=True,
            check=False,
        )
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertTrue(r.stderr.startswith(b"notes: error: "), r.stderr)
        self.assertEqual(len(r.stderr.splitlines()), 1)
        self.assertFalse(os.path.exists(self.path))

    def test_broken_pipe_is_silent_exit_1(self):
        with open(self.path, "w") as f:
            json.dump(
                {"notes": [{"id": i, "text": f"note {i}"} for i in range(1, 20001)]}, f
            )
        env = dict(os.environ, **self.env)
        p = subprocess.Popen(
            [sys.executable, "-m", "sandbox", "notes", "list"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        first = p.stdout.readline()
        p.stdout.close()
        err = p.stderr.read()
        p.stderr.close()
        code = p.wait()
        self.assertEqual(first, b"1\tnote 1\n")
        self.assertEqual(err, b"")
        self.assertEqual(code, 1)

    def test_ascii_output_encoding_error(self):
        self.assertEqual(sandbox("notes", "add", "café", env=self.env).returncode, 0)
        r = sandbox("notes", "list", env=dict(self.env, PYTHONIOENCODING="ascii"))
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith(b"notes: error: "), r.stderr)
        self.assertEqual(len(r.stderr.splitlines()), 1, r.stderr)
        self.assertNotIn(b"Traceback", r.stderr)

    def test_closed_stdout_fails_and_writes_nothing(self):
        r = subprocess.run(
            f'"{sys.executable}" -m sandbox notes add x >&-',
            shell=True,
            cwd=ROOT,
            env=dict(os.environ, **self.env),
            capture_output=True,
            check=False,
        )
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stderr.count(b"\n"), 1, r.stderr)
        self.assertTrue(r.stderr.startswith(b"notes: error: "), r.stderr)
        self.assertFalse(os.path.exists(self.path))

    def test_valid_paths_exit_codes_unchanged(self):
        self.assertEqual(
            sandbox("notes", "add", "buy milk", env=self.env).returncode, 0
        )
        self.assertEqual(sandbox("notes", "search", "milk", env=self.env).returncode, 0)
        self.assertEqual(
            sandbox("notes", "search", "zebra", env=self.env).returncode, 1
        )
        self.assertEqual(sandbox("notes", "add", "  ", env=self.env).returncode, 2)


if __name__ == "__main__":
    unittest.main()
