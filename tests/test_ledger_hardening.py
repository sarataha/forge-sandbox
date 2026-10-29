import os
import subprocess
import sys

from tests.ledger_support import LedgerTestCase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ControlCharTest(LedgerTestCase):
    def assert_rejected(self, r, kind, raw):
        self.assertEqual((r.code, r.out), (1, ""))
        self.assertEqual(r.err, f"ledger: error: bad {kind} '{raw}'\n")
        self.assertEqual(self.run_cli("list").out, "")

    def test_category_rejects_non_printable(self):
        for ch, esc in (("\x1b", "\\x1b"), ("\x00", "\\x00"), (" ", "\\u2028")):
            r = self.run_cli("add", "5", f"fo{ch}od")
            self.assert_rejected(r, "category", f"fo{esc}od")

    def test_note_rejects_non_printable(self):
        for ch, esc in (("\x1b", "\\x1b"), ("\x00", "\\x00"), (" ", "\\u2028")):
            r = self.run_cli("add", "5", "food", "--note", f"a{ch}b")
            self.assert_rejected(r, "note", f"a{esc}b")

    def test_budget_set_rejects(self):
        r = self.run_cli("budget", "set", "fo\x1bod", "5")
        self.assertEqual((r.code, r.out), (1, ""))
        self.assertEqual(r.err, "ledger: error: bad category 'fo\\x1bod'\n")

    def test_import_rejects_and_stores_nothing(self):
        path = self.write_file(
            "a.csv", "date,amount,category,note\n2026-10-03,5,tea,a\x1bb\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual((r.code, r.out), (1, ""))
        self.assertEqual(r.err.count("\n"), 1)
        self.assertTrue(r.err.startswith("ledger: error: "))
        self.assertEqual(self.run_cli("list").out, "")

    def test_plain_spaces_still_allowed(self):
        r = self.run_cli("add", "5", "hot  food", "--note", "two words")
        self.assertEqual(r.code, 0)


class HugeAmountTest(LedgerTestCase):
    def test_huge_amount_is_bad_amount(self):
        r = self.run_cli("add", "9" * 5000, "food")
        self.assertEqual((r.code, r.out), (1, ""))
        self.assertEqual(r.err.count("\n"), 1)
        self.assertTrue(r.err.startswith("ledger: error: bad amount '"))
        self.assertNotIn("Traceback", r.err)
        self.assertEqual(self.run_cli("list").out, "")

    def test_huge_amount_in_import(self):
        path = self.write_file(
            "a.csv", "date,amount,category,note\n2026-10-03," + "9" * 5000 + ",tea,\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual((r.code, r.out), (1, ""))
        self.assertEqual(r.err.count("\n"), 1)
        self.assertEqual(self.run_cli("list").out, "")

    def test_cap_still_accepted(self):
        self.assertEqual(self.run_cli("add", "99999999.99", "food").code, 0)
        self.assertEqual(self.run_cli("add", "100000000", "food").code, 1)


class BrokenPipeTest(LedgerTestCase):
    def test_list_into_closed_reader_is_quiet(self):
        rows = "".join(f"2026-10-01,1.{i % 100:02d},food,n{i}\n" for i in range(5000))
        path = self.write_file("big.csv", "date,amount,category,note\n" + rows)
        env = {**os.environ, "SANDBOX_LEDGER_DB": self.db_path, "PYTHONPATH": REPO}
        env.pop("SANDBOX_LICENSE_KEY", None)
        cmd = [sys.executable, "-m", "sandbox", "ledger"]
        imp = subprocess.run(
            [*cmd, "import", path],
            check=False,
            env=env,
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(imp.returncode, 0, imp.stderr)

        writer = subprocess.Popen(
            [*cmd, "list"],
            env=env,
            cwd=REPO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        first = writer.stdout.readline()
        writer.stdout.close()
        err = writer.stderr.read()
        writer.stderr.close()
        writer.wait()
        self.assertTrue(first)
        self.assertEqual(err, "")
        self.assertNotIn("Traceback", err)
