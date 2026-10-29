import sqlite3

from sandbox.ledger.store import open_store
from tests.ledger_support import LedgerTestCase


class EmptyDateTest(LedgerTestCase):
    def test_empty_date_is_rejected_not_today(self):
        r = self.run_cli("add", "5", "food", "--date", "")
        self.assertEqual(
            (r.code, r.out, r.err), (1, "", "ledger: error: bad date ''\n")
        )
        self.assertEqual(self.run_cli("list").out, "")


class ErrorMessageEscapeTest(LedgerTestCase):
    def assert_one_line(self, r, message):
        self.assertEqual((r.code, r.out), (1, ""))
        self.assertEqual(r.err, f"ledger: error: {message}\n")

    def test_plain_text_keeps_form(self):
        self.assert_one_line(
            self.run_cli("add", "12.5.0", "food"), "bad amount '12.5.0'"
        )

    def test_control_chars_escaped(self):
        self.assert_one_line(self.run_cli("add", "1\t2", "food"), "bad amount '1\\t2'")
        self.assert_one_line(
            self.run_cli("add", "5", "fo\nod"), "bad category 'fo\\nod'"
        )
        self.assert_one_line(
            self.run_cli("add", "5", "food", "--note", "a\rb"), "bad note 'a\\rb'"
        )
        self.assert_one_line(
            self.run_cli("add", "5", "food", "--date", "2026\t"), "bad date '2026\\t'"
        )


class SchemaVersionTest(LedgerTestCase):
    def test_schema_created_once(self):
        open_store(self.db_path).close()
        con = sqlite3.connect(self.db_path)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 1)
        con.execute("DROP INDEX expense_date")
        con.commit()
        con.close()
        self.assertEqual(
            self.run_cli("add", "5", "food", "--date", "2026-10-01").code, 0
        )
        con = sqlite3.connect(self.db_path)
        found = con.execute(
            "SELECT name FROM sqlite_master WHERE name = 'expense_date'"
        ).fetchall()
        con.close()
        self.assertEqual(found, [])
