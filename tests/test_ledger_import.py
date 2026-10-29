import os
import unittest

from tests.ledger_support import LedgerTestCase

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "expenses.csv")

# Hand-written from the fixture file, in (date, id) order.
FIXTURE_LIST = (
    "2026-10-01\t9.99\tgroceries\tbread\n"
    "2026-10-02\t4.50\tcoffee\t\n"
    "2026-10-04\t25.00\tgroceries\tweekly shop\n"
    "2026-10-07\t60.00\tutilities\telectric\n"
    "2026-10-09\t15.25\ttransport\ttrain\n"
    "2026-10-12\t32.80\tdining\tlunch\n"
)

HEADER = "date,amount,category,note\n"


class ImportTest(LedgerTestCase):
    def assert_rejected(self, path, line, reason, before=""):
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertEqual(r.err, f"ledger: error: {path} line {line}: {reason}\n")
        self.assertEqual(self.run_cli("list").out, before)

    # Acceptance 1
    def test_fixture_imports_every_row(self):
        r = self.run_cli("import", FIXTURE)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 6, skipped 0 duplicates\n")
        self.assertEqual(r.err, "")
        self.assertEqual(self.run_cli("list").out, FIXTURE_LIST)

    # Acceptance 2
    def test_reimport_skips_everything_and_stores_nothing(self):
        self.run_cli("import", FIXTURE)
        r = self.run_cli("import", FIXTURE)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 0, skipped 6 duplicates\n")
        self.assertEqual(self.run_cli("list").out, FIXTURE_LIST)

    # Acceptance 3
    def test_identical_rows_into_empty_ledger_import_both(self):
        path = self.write_file(
            "dup.csv", HEADER + "2026-10-03,5.00,tea,\n2026-10-03,5.00,tea,\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 2, skipped 0 duplicates\n")
        self.assertEqual(self.run_cli("list").out, "2026-10-03\t5.00\ttea\t\n" * 2)

    def test_existing_copies_are_skipped_and_the_rest_imported(self):
        self.run_cli("add", "5", "tea", "--date", "2026-10-03")
        self.run_cli("add", "5", "tea", "--date", "2026-10-03")
        row = "2026-10-03,5.00,tea,\n"
        path = self.write_file("three.csv", HEADER + row * 3)
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 1, skipped 2 duplicates\n")
        self.assertEqual(self.run_cli("list").out, "2026-10-03\t5.00\ttea\t\n" * 3)

    def test_fewer_rows_in_file_than_in_db_skips_them_all(self):
        self.run_cli("add", "5", "tea", "--date", "2026-10-03")
        self.run_cli("add", "5", "tea", "--date", "2026-10-03")
        path = self.write_file("one.csv", HEADER + "2026-10-03,5.00,tea,\n")
        r = self.run_cli("import", path)
        self.assertEqual(r.out, "imported 0, skipped 1 duplicates\n")
        self.assertEqual(self.run_cli("list").out, "2026-10-03\t5.00\ttea\t\n" * 2)

    def test_duplicate_matches_on_amount_value_and_category_case(self):
        self.run_cli(
            "add", "12.5", "Groceries", "--date", "2026-10-03", "--note", "market"
        )
        path = self.write_file(
            "same.csv", HEADER + "2026-10-03,12.50,groceries,market\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.out, "imported 0, skipped 1 duplicates\n")

    def test_different_note_is_not_a_duplicate(self):
        self.run_cli(
            "add", "12.50", "groceries", "--date", "2026-10-03", "--note", "market"
        )
        path = self.write_file("note.csv", HEADER + "2026-10-03,12.50,groceries,shop\n")
        r = self.run_cli("import", path)
        self.assertEqual(r.out, "imported 1, skipped 0 duplicates\n")

    # Acceptance 4
    def test_utf8_bom_imports_the_same(self):
        text = HEADER + "2026-10-03,12.50,groceries,market\n"
        plain = self.write_file("plain.csv", text)
        bom = self.write_file("bom.csv", text, encoding="utf-8-sig")
        with open(bom, "rb") as f:
            self.assertTrue(f.read().startswith(b"\xef\xbb\xbf"))
        r = self.run_cli("import", bom)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 1, skipped 0 duplicates\n")
        listed = self.run_cli("list").out
        self.assertEqual(listed, "2026-10-03\t12.50\tgroceries\tmarket\n")
        again = self.run_cli("import", plain)
        self.assertEqual(again.out, "imported 0, skipped 1 duplicates\n")
        self.assertEqual(self.run_cli("list").out, listed)

    # Acceptance 5
    def test_bad_amount_names_line_and_imports_nothing(self):
        rows = "".join(f"2026-10-0{i},{i}.00,food,\n" for i in range(1, 6))
        path = self.write_file("bad.csv", HEADER + rows + "2026-10-07,12.5.0,food,\n")
        # Header is line 1, five good rows are lines 2-6, the bad row is line 7.
        self.assert_rejected(path, 7, "bad amount '12.5.0'")

    def test_bad_date_names_line_and_imports_nothing(self):
        path = self.write_file(
            "bad.csv", HEADER + "2026-10-03,5.00,tea,\n2026-02-30,5.00,tea,\n"
        )
        self.assert_rejected(path, 3, "bad date '2026-02-30'")

    def test_non_iso_dates_are_rejected(self):
        for bad in ("03/10/2026", "20261003", "2026-W40-1", "2026-13-01"):
            with self.subTest(date=bad):
                path = self.write_file("bad.csv", HEADER + f"{bad},5.00,tea,\n")
                self.assert_rejected(path, 2, f"bad date '{bad}'")

    def test_row_with_missing_column_is_rejected(self):
        path = self.write_file(
            "short.csv", HEADER + "2026-10-03,5.00,tea,\n2026-10-04,5.00\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertTrue(r.err.startswith(f"ledger: error: {path} line 3: "), r.err)
        self.assertEqual(self.run_cli("list").out, "")

    def test_header_missing_amount_column_is_rejected(self):
        path = self.write_file("noamount.csv", "date,category,note\n2026-10-03,tea,\n")
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertIn("missing column 'amount'", r.err)
        self.assertEqual(self.run_cli("list").out, "")

    def test_bad_row_leaves_existing_expenses_untouched(self):
        self.run_cli("add", "5", "tea", "--date", "2026-10-03")
        path = self.write_file(
            "bad.csv", HEADER + "2026-10-04,6.00,tea,\n2026-10-05,x,tea,\n"
        )
        self.assert_rejected(
            path, 3, "bad amount 'x'", before="2026-10-03\t5.00\ttea\t\n"
        )

    def test_row_with_too_many_fields_is_rejected(self):
        path = self.write_file("wide.csv", HEADER + "2026-10-03,5.00,tea,,extra\n")
        self.assert_rejected(path, 2, "too many fields")

    def test_blank_category_is_rejected(self):
        path = self.write_file("nocat.csv", HEADER + "2026-10-03,5.00,   ,\n")
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertTrue(r.err.startswith(f"ledger: error: {path} line 2: "), r.err)
        self.assertEqual(self.run_cli("list").out, "")

    def test_newline_in_quoted_note_is_rejected(self):
        path = self.write_file("nl.csv", HEADER + '2026-10-03,5.00,tea,"a\nb"\n')
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertEqual(self.run_cli("list").out, "")

    # Header and file rules (architecture: Data model, Review focus)
    def test_header_is_case_insensitive_without_note_column(self):
        path = self.write_file("h.csv", "Date,Amount,Category\n2026-10-03,5,tea\n")
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 1, skipped 0 duplicates\n")
        self.assertEqual(self.run_cli("list").out, "2026-10-03\t5.00\ttea\t\n")

    def test_columns_in_any_order_and_extra_columns_ignored(self):
        path = self.write_file(
            "order.csv",
            "category,account,note,amount,date\ntea,main,hot,5.00,2026-10-03\n",
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.run_cli("list").out, "2026-10-03\t5.00\ttea\thot\n")

    def test_repeated_required_column_is_rejected(self):
        path = self.write_file(
            "rep.csv", "date,amount,amount,category\n2026-10-03,5,6,tea\n"
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")

    def test_blank_lines_are_skipped(self):
        path = self.write_file("blank.csv", HEADER + "\n2026-10-03,5.00,tea,\n\n")
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 1, skipped 0 duplicates\n")

    def test_header_only_imports_nothing(self):
        path = self.write_file("hdr.csv", HEADER)
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "imported 0, skipped 0 duplicates\n")

    def test_empty_file_is_rejected(self):
        path = self.write_file("empty.csv", "")
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertTrue(r.err.startswith("ledger: error: "), r.err)

    def test_latin1_file_is_rejected(self):
        path = self.write_file(
            "latin.csv", HEADER + "2026-10-03,5.00,caf\xe9,\n", encoding="latin-1"
        )
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertEqual(r.err, f"ledger: error: {path}: not UTF-8\n")
        self.assertEqual(self.run_cli("list").out, "")

    def test_missing_file_is_rejected(self):
        path = os.path.join(self.tmp_dir, "nope.csv")
        r = self.run_cli("import", path)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.out, "")
        self.assertTrue(r.err.startswith(f"ledger: error: cannot read {path}"), r.err)


if __name__ == "__main__":
    unittest.main()
