import io
import os
import sqlite3
import unittest
from contextlib import redirect_stdout
from datetime import date

from sandbox.__main__ import main
from tests.ledger_support import LedgerTestCase


class AddListTest(LedgerTestCase):
    def assert_rejected(self, *argv):
        r = self.run_cli(*argv)
        self.assertEqual(r.code, 1, argv)
        self.assertEqual(r.out, "", argv)
        self.assertTrue(r.err.startswith("ledger: error: "), r.err)
        self.assertEqual(len(r.err.strip().splitlines()), 1, r.err)
        listed = self.run_cli("list")
        self.assertEqual(listed.code, 0)
        self.assertEqual(listed.out, "", argv)

    def test_add_with_date_and_note_is_stored(self):
        r = self.run_cli("add", "12.50", "groceries", "--date", "2026-10-03", "--note", "market")
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, "added 1 2026-10-03 12.50 groceries\n")
        self.assertEqual(self.run_cli("list").out, "2026-10-03\t12.50\tgroceries\tmarket\n")

    def test_add_without_date_uses_today(self):
        r = self.run_cli("add", "40", "transport")
        today = date.today().isoformat()
        self.assertEqual(r.code, 0)
        self.assertEqual(self.run_cli("list").out, f"{today}\t40.00\ttransport\t\n")

    def test_category_is_case_insensitive(self):
        self.run_cli("add", "5", "Groceries", "--date", "2026-10-01")
        self.run_cli("add", "6", "groceries", "--date", "2026-10-02")
        self.assertEqual(
            self.run_cli("list").out,
            "2026-10-01\t5.00\tgroceries\t\n2026-10-02\t6.00\tgroceries\t\n",
        )

    def test_list_orders_oldest_first_with_two_decimals(self):
        self.run_cli("add", "40", "transport", "--date", "2026-10-05")
        self.run_cli("add", "12.50", "groceries", "--date", "2026-10-03", "--note", "market")
        r = self.run_cli("list")
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, "2026-10-03\t12.50\tgroceries\tmarket\n2026-10-05\t40.00\ttransport\t\n")

    def test_list_empty_prints_nothing(self):
        r = self.run_cli("list")
        self.assertEqual((r.code, r.out), (0, ""))

    def test_invalid_amounts_exit_1_and_store_nothing(self):
        for amount in ("12.5.0", "-3", "0", "abc"):
            with self.subTest(amount=amount):
                self.assert_rejected("add", amount, "groceries", "--date", "2026-10-03")
                self.assertIn(f"bad amount '{amount}'", self.run_cli("add", amount, "x").err)

    def test_invalid_dates_exit_1_and_store_nothing(self):
        for bad in ("2026-13-01", "03/10/2026"):
            with self.subTest(date=bad):
                self.assert_rejected("add", "5", "groceries", "--date", bad)
                self.assertIn(f"bad date '{bad}'", self.run_cli("add", "5", "x", "--date", bad).err)

    def test_db_defaults_to_local_file_and_schema_created_on_first_use(self):
        os.environ.pop("SANDBOX_LEDGER_DB")
        cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        self.addCleanup(os.chdir, cwd)
        self.assertFalse(os.path.exists("ledger.db"))
        r = self.run_cli("add", "5", "groceries", "--date", "2026-10-01")
        self.assertEqual(r.code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "ledger.db")))
        self.assertEqual(self.run_cli("list").out, "2026-10-01\t5.00\tgroceries\t\n")

    def test_db_and_schema_created_at_configured_path(self):
        self.assertFalse(os.path.exists(self.db_path))
        self.assertEqual(self.run_cli("list").code, 0)
        self.assertTrue(os.path.exists(self.db_path))
        con = sqlite3.connect(self.db_path)
        self.addCleanup(con.close)
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertLessEqual({"expense", "budget"}, tables)

    def test_greet_still_works(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(main(["greet", "ada"]), 0)
        self.assertEqual(buf.getvalue(), "hello, ada\n")


if __name__ == "__main__":
    unittest.main()
