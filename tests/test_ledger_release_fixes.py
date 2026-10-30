import os
import subprocess
import sys
import tempfile
import unicodedata
import unittest

from tests.ledger_support import LedgerTestCase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NBSP = chr(0xA0)
ZWJ = chr(0x200D)
ZWNJ = chr(0x200C)

ACCEPTED = {
    "nbsp": "a" + NBSP + "b",
    "narrow nbsp": "a" + chr(0x202F) + "b",
    "ideographic space": "a" + chr(0x3000) + "b",
    "zwj emoji": chr(0x1F468) + ZWJ + chr(0x1F469) + ZWJ + chr(0x1F467),
    "zwnj persian": "".join(chr(c) for c in (0x645, 0x6CC))
    + ZWNJ
    + "".join(chr(c) for c in (0x62E, 0x648, 0x631, 0x645)),
    "lrm": "a" + chr(0x200E) + "b",
    "rlm": "a" + chr(0x200F) + "b",
    "england flag": chr(0x1F3F4)
    + "".join(chr(c) for c in (0xE0067, 0xE0062, 0xE0065, 0xE006E, 0xE0067, 0xE007F)),
    "unassigned": "a" + chr(0x0378) + "b",
}
REJECTED = {
    "soft hyphen": "co" + chr(0xAD) + "op",
    "lre": "a" + chr(0x202A) + "b",
    "rlo": "a" + chr(0x202E) + "b",
    "lri": "a" + chr(0x2066) + "b",
    "pdi": "a" + chr(0x2069) + "b",
    "bom": "a" + chr(0xFEFF) + "b",
    "zero width space": "a" + chr(0x200B) + "b",
    "private use": "a" + chr(0xE000) + "b",
    "lone surrogate": "a" + chr(0xD800) + "b",
    "esc": "a" + chr(0x1B) + "b",
    "nul": "a" + chr(0) + "b",
    "line separator": "a" + chr(0x2028) + "b",
    "paragraph separator": "a" + chr(0x2029) + "b",
}


class BrokenPipeSmallOutputTest(unittest.TestCase):
    def test_one_row_list_into_closed_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "SANDBOX_LEDGER_DB": os.path.join(tmp, "l.db")}
            add = subprocess.run(
                [sys.executable, "-m", "sandbox", "ledger", "add", "1.00", "x"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                check=False,
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            proc = subprocess.Popen(
                [sys.executable, "-m", "sandbox", "ledger", "list"],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            proc.stdout.close()
            err = proc.stderr.read().decode()
            proc.stderr.close()
            code = proc.wait()
        self.assertEqual(err, "")
        self.assertNotIn("Traceback", err)
        self.assertNotIn("Exception ignored", err)
        self.assertNotEqual(code, 120)


class ClosedStdoutTest(unittest.TestCase):
    def test_closed_stdout_is_silent_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "SANDBOX_LEDGER_DB": os.path.join(tmp, "l.db")}
            cmd = f"'{sys.executable}' -m sandbox ledger list >&-"
            p = subprocess.run(
                ["/bin/sh", "-c", cmd],
                cwd=ROOT,
                env=env,
                capture_output=True,
                check=False,
            )
        self.assertEqual(p.stderr, b"")
        self.assertEqual(p.returncode, 1)


class UnencodableOutputTest(unittest.TestCase):
    def test_ascii_stdout_gives_one_line_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **os.environ,
                "SANDBOX_LEDGER_DB": os.path.join(tmp, "l.db"),
                "PYTHONIOENCODING": "ascii:strict",
            }
            p = subprocess.run(
                [sys.executable, "-m", "sandbox", "ledger", "add", "1", "café"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                check=False,
            )
        self.assertEqual(p.returncode, 1)
        self.assertNotIn(b"Traceback", p.stderr)
        self.assertTrue(p.stderr.startswith(b"ledger: error:"))


class UnicodeTextTest(LedgerTestCase):
    def test_accepted_in_category_and_note(self):
        for name, text in ACCEPTED.items():
            with self.subTest(name):
                r = self.run_cli(
                    "add", "1.00", text, "--note", text, "--date", "2026-01-01"
                )
                self.assertEqual(r.code, 0, r.err)
                lst = self.run_cli("list")
                cat = unicodedata.normalize("NFKC", text).casefold()
                self.assertIn(f"\t{cat}\t{text}\n", lst.out)

    def test_rejected(self):
        for name, text in REJECTED.items():
            with self.subTest(name + " category"):
                r = self.run_cli("add", "1.00", text)
                self.assertEqual(r.code, 1)
                self.assertEqual(len(r.err.splitlines()), 1)
            with self.subTest(name + " note"):
                r = self.run_cli("add", "1.00", "x", "--note", text)
                self.assertEqual(r.code, 1)
                self.assertEqual(len(r.err.splitlines()), 1)
        self.assertEqual(self.run_cli("list").out, "")

    def test_nbsp_and_space_category_are_one(self):
        a = self.run_cli("add", "1.00", "eating" + NBSP + "out", "--date", "2026-01-01")
        b = self.run_cli("add", "2.00", "eating out", "--date", "2026-01-02")
        self.assertEqual((a.code, b.code), (0, 0))
        out = self.run_cli("list").out
        self.assertEqual(out.count("\teating out\t"), 2)
        self.assertEqual(
            self.run_cli("budget", "set", "eating" + NBSP + "out", "9").code, 0
        )
        self.assertEqual(self.run_cli("budget", "list").out, "eating out\t9.00\n")

    def test_category_is_nfkc_stable_after_casefold(self):
        r = self.run_cli("add", "1.00", chr(0x1F0), "--date", "2026-01-01")
        self.assertEqual(r.code, 0, r.err)
        self.assertIn(f"\t{chr(0x1F0)}\t", self.run_cli("list").out)

    def test_csv_import_nbsp_note(self):
        note = "a" + NBSP + "b"
        path = self.write_file(
            "n.csv", f"date,amount,category,note\n2026-01-01,5.00,food,{note}\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r.err)
        self.assertIn(f"food\t{note}\n", self.run_cli("list").out)


class AmountLeadingZerosTest(LedgerTestCase):
    def test_leading_zeros_accepted(self):
        for text, want in (("000000001", "1.00"), ("000000012.50", "12.50")):
            with self.subTest(text):
                self.assertEqual(
                    self.run_cli("add", text, "x", "--date", "2026-01-01").code, 0
                )
                self.assertIn(f"\t{want}\tx", self.run_cli("list").out)

    def test_huge_zero_padded_amount_is_small_value(self):
        text = "0" * 5000 + "5"
        r = self.run_cli("add", text, "x", "--date", "2026-01-01")
        self.assertEqual(r.code, 0, r.err)
        self.assertIn("\t5.00\tx", self.run_cli("list").out)
        b = self.run_cli("budget", "set", "x", text)
        self.assertEqual(b.code, 0, b.err)
        self.assertEqual(self.run_cli("budget", "list").out, "x\t5.00\n")
        path = self.write_file(
            "z.csv", f"date,amount,category,note\n2026-01-02,{text},y,\n"
        )
        i = self.run_cli("import", path)
        self.assertEqual(i.code, 0, i.err)
        self.assertIn("\t5.00\ty\t", self.run_cli("list").out)

    def test_huge_amount_one_line(self):
        r = self.run_cli("add", "9" * 5000, "x")
        self.assertEqual(r.code, 1)
        self.assertEqual(len(r.err.splitlines()), 1)
        self.assertIn("bad amount", r.err)


if __name__ == "__main__":
    unittest.main()
