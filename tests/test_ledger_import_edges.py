from tests.ledger_support import LedgerTestCase

HEADER = "date,amount,category,note\n"


class ImportEdgesTest(LedgerTestCase):
    def listed(self):
        return self.run_cli("list").out

    def test_whitespace_only_line_is_skipped(self):
        path = self.write_file("a.csv", HEADER + "   \n2026-10-03,5,tea,\n")
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 0, res.err)
        self.assertEqual(res.out, "imported 1, skipped 0 duplicates\n")

    def test_leading_blank_lines_before_header(self):
        path = self.write_file("a.csv", "\n  \n" + HEADER + "2026-10-03,5,tea,\n")
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 0, res.err)
        self.assertEqual(res.out, "imported 1, skipped 0 duplicates\n")

    def test_only_blank_lines_is_empty_file(self):
        path = self.write_file("a.csv", "\n   \n")
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 1)
        self.assertIn(f"{path}: empty file", res.err)

    def test_repeated_note_header_is_error(self):
        path = self.write_file(
            "a.csv", "date,amount,category,note,note\n2026-10-03,5,tea,a,b\n"
        )
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 1)
        self.assertIn("repeated column 'note'", res.err)
        self.assertEqual(self.listed(), "")

    def test_short_row_names_missing_column(self):
        path = self.write_file(
            "a.csv", "date,amount,category,note,tag\n2026-10-03,5,tea,hi\n"
        )
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 1)
        self.assertIn(f"{path} line 2: missing column 'tag'", res.err)
        self.assertEqual(self.listed(), "")

    def test_date_cell_is_stripped(self):
        path = self.write_file("a.csv", HEADER + " 2026-10-03,5,tea,\n")
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 0, res.err)
        self.assertEqual(res.out, "imported 1, skipped 0 duplicates\n")

    def test_malformed_quoted_field_is_bad_row(self):
        path = self.write_file(
            "a.csv", HEADER + "2026-10-03,5,tea,\n" + '2026-10-04,5,tea,"abc"def\n'
        )
        res = self.run_cli("import", path)
        self.assertEqual(res.code, 1)
        self.assertIn(f"{path} line 3:", res.err)
        self.assertEqual(self.listed(), "")
