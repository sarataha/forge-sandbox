import os
import unittest

from tests.ledger_support import LedgerTestCase

HEADER = "date,amount,category,note\n"

EMPTY_JSON = '{\n  "expenses": [],\n  "format": "ledger-export",\n  "version": 1\n}\n'


class ExportTest(LedgerTestCase):
    def add(self, amount, category, date, note=None):
        argv = ["add", amount, category, "--date", date]
        if note is not None:
            argv += ["--note", note]
        self.assertEqual(self.run_cli(*argv).code, 0)

    def seed_unordered(self):
        # Added out of date order; two on the same date to pin the id tie-break.
        self.add("40", "transport", "2026-10-05")
        self.add("12.5", "groceries", "2026-10-03", "market")
        self.add("3", "coffee", "2026-10-03")

    # Acceptance 1
    def test_csv_header_and_rows_oldest_date_first(self):
        self.seed_unordered()
        r = self.run_cli("export", "--format", "csv")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.err, "")
        self.assertEqual(
            r.out,
            HEADER
            + "2026-10-03,12.50,groceries,market\n"
            + "2026-10-03,3.00,coffee,\n"
            + "2026-10-05,40.00,transport,\n",
        )

    # Acceptance 1
    def test_csv_is_the_default_format(self):
        self.add("12.5", "groceries", "2026-10-03", "market")
        r = self.run_cli("export")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, HEADER + "2026-10-03,12.50,groceries,market\n")

    # Acceptance 1
    def test_csv_quotes_comma_and_quote_in_note(self):
        self.add("12.50", "groceries", "2026-10-03", 'market, "fresh"')
        r = self.run_cli("export", "--format", "csv")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(
            r.out, HEADER + '2026-10-03,12.50,groceries,"market, ""fresh"""\n'
        )

    # Acceptance 1
    def test_csv_has_no_bom_and_no_carriage_returns(self):
        self.add("12.5", "groceries", "2026-10-03")
        out = self.run_cli("export", "--format", "csv").out
        self.assertFalse(out.startswith("﻿"))
        self.assertNotIn("\r", out)

    # Acceptance 2
    def test_json_shape_oldest_date_first(self):
        self.seed_unordered()
        r = self.run_cli("export", "--format", "json")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.err, "")
        self.assertEqual(
            r.out,
            "{\n"
            '  "expenses": [\n'
            "    {\n"
            '      "amount_cents": 1250,\n'
            '      "category": "groceries",\n'
            '      "date": "2026-10-03",\n'
            '      "note": "market"\n'
            "    },\n"
            "    {\n"
            '      "amount_cents": 300,\n'
            '      "category": "coffee",\n'
            '      "date": "2026-10-03",\n'
            '      "note": ""\n'
            "    },\n"
            "    {\n"
            '      "amount_cents": 4000,\n'
            '      "category": "transport",\n'
            '      "date": "2026-10-05",\n'
            '      "note": ""\n'
            "    }\n"
            "  ],\n"
            '  "format": "ledger-export",\n'
            '  "version": 1\n'
            "}\n",
        )

    # Acceptance 2
    def test_json_escapes_note_and_keeps_non_ascii(self):
        self.add("12.50", "café", "2026-10-03", 'market, "fresh"')
        r = self.run_cli("export", "--format", "json")
        self.assertEqual(r.code, 0, r)
        self.assertIn('"category": "café"', r.out)
        self.assertIn('"note": "market, \\"fresh\\""', r.out)

    # Acceptance 3
    def test_csv_round_trip_into_empty_ledger(self):
        self.seed_unordered()
        self.add("12.5", "groceries", "2026-10-03", "market")  # identical twin
        self.add("9.99", "dining", "2026-09-30", 'say "hi", ok')
        exported = self.run_cli("export", "--format", "csv").out
        original_list = self.run_cli("list").out
        path = self.write_file("export.csv", exported)

        other = os.path.join(self.tmp_dir, "second.db")
        r = self.run_cli("import", path, env={"SANDBOX_LEDGER_DB": other})
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 5, skipped 0 duplicates\n")
        self.assertEqual(
            self.run_cli("list", env={"SANDBOX_LEDGER_DB": other}).out, original_list
        )
        again = self.run_cli(
            "export", "--format", "csv", env={"SANDBOX_LEDGER_DB": other}
        )
        self.assertEqual(again.out, exported)

    # Acceptance 4
    def test_note_with_comma_and_quotes_survives_round_trip(self):
        note = 'market, "fresh", 2 for 1'
        self.add("12.50", "groceries", "2026-10-03", note)
        path = self.write_file("export.csv", self.run_cli("export").out)

        other = os.path.join(self.tmp_dir, "second.db")
        r = self.run_cli("import", path, env={"SANDBOX_LEDGER_DB": other})
        self.assertEqual(r.code, 0, r)
        listed = self.run_cli("list", env={"SANDBOX_LEDGER_DB": other}).out
        self.assertEqual(listed, f"2026-10-03\t12.50\tgroceries\t{note}\n")

    # Acceptance 5
    def test_empty_ledger_csv_is_header_only(self):
        r = self.run_cli("export", "--format", "csv")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, HEADER)
        self.assertEqual(r.err, "")

    # Acceptance 5
    def test_empty_ledger_json_has_no_expenses(self):
        r = self.run_cli("export", "--format", "json")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, EMPTY_JSON)
        self.assertEqual(r.err, "")

    # Acceptance 5 (default format on an empty ledger)
    def test_empty_ledger_default_is_header_only_csv(self):
        r = self.run_cli("export")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, HEADER)

    # Review focus: unknown format is an argparse usage error
    def test_unknown_format_is_a_usage_error(self):
        r = self.run_cli("export", "--format", "xml")
        self.assertEqual(r.code, 2, r)
        self.assertEqual(r.out, "")
        self.assertIn("argument --format: invalid choice", r.err)


if __name__ == "__main__":
    unittest.main()
