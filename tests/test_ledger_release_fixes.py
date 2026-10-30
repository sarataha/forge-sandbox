import os
import subprocess
import sys
import tempfile
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
    "soft hyphen": "co" + chr(0xAD) + "op",
    "rlm": "a" + chr(0x200F) + "b",
}
REJECTED = {
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


class UnicodeTextTest(LedgerTestCase):
    def test_accepted_in_category_and_note(self):
        for name, text in ACCEPTED.items():
            with self.subTest(name):
                r = self.run_cli(
                    "add", "1.00", text, "--note", text, "--date", "2026-01-01"
                )
                self.assertEqual(r.code, 0, r.err)
                lst = self.run_cli("list")
                self.assertIn(f"\t{text.casefold()}\t{text}\n", lst.out)

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

    def test_huge_amount_one_line(self):
        r = self.run_cli("add", "9" * 5000, "x")
        self.assertEqual(r.code, 1)
        self.assertEqual(len(r.err.splitlines()), 1)
        self.assertIn("bad amount", r.err)


if __name__ == "__main__":
    unittest.main()
