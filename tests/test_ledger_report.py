from tests.ledger_support import LedgerTestCase

HEADER = "category\tspent\tbudget\tremaining\n"


class ReportTest(LedgerTestCase):
    def add(self, amount, category, date):
        r = self.run_cli("add", amount, category, "--date", date)
        self.assertEqual(r.code, 0, r.err)

    def budget(self, category, amount):
        r = self.run_cli("budget", "set", category, amount)
        self.assertEqual(r.code, 0, r.err)

    def report(self, month="2026-10"):
        return self.run_cli("report", "--month", month)

    def assert_bad_month(self, month):
        r = self.run_cli("report", "--month", month)
        self.assertEqual(r.code, 1, month)
        self.assertEqual(r.out, "", month)
        self.assertTrue(r.err.startswith("ledger: error: "), r.err)
        self.assertEqual(len(r.err.strip().splitlines()), 1, r.err)

    # Acceptance 1: one line per Category with Expenses or a Budget, two decimals
    def test_full_report_matches_architecture_example(self):
        self.add("12.50", "groceries", "2026-10-03")
        self.add("900", "rent", "2026-10-01")
        self.add("40", "transport", "2026-10-05")
        self.budget("groceries", "200")
        self.budget("rent", "800")
        r = self.report()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.err, "")
        self.assertEqual(
            r.out,
            HEADER
            + "groceries\t12.50\t200.00\t187.50\n"
            + "rent\t900.00\t800.00\t-100.00\tOVER\n"
            + "transport\t40.00\t-\t-\n"
            + "TOTAL\t952.50\t1000.00\t87.50\n",
        )

    def test_category_with_budget_but_no_expenses_has_a_line(self):
        self.budget("groceries", "200")
        r = self.report()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(
            r.out,
            HEADER
            + "groceries\t0.00\t200.00\t200.00\n"
            + "TOTAL\t0.00\t200.00\t200.00\n",
        )

    def test_category_with_expenses_but_no_budget_has_a_line(self):
        self.add("40", "transport", "2026-10-05")
        r = self.report()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(
            r.out, HEADER + "transport\t40.00\t-\t-\n" + "TOTAL\t40.00\t-\t-\n"
        )

    def test_lines_are_sorted_by_category(self):
        self.add("1", "zeta", "2026-10-02")
        self.add("2", "alpha", "2026-10-02")
        self.budget("mid", "3")
        lines = self.report().out.splitlines()
        self.assertEqual(
            [ln.split("\t")[0] for ln in lines],
            ["category", "alpha", "mid", "zeta", "TOTAL"],
        )

    def test_amounts_use_two_decimals(self):
        self.add("5", "groceries", "2026-10-02")
        self.budget("groceries", "7.5")
        r = self.report()
        self.assertEqual(
            r.out,
            HEADER + "groceries\t5.00\t7.50\t2.50\n" + "TOTAL\t5.00\t7.50\t2.50\n",
        )

    def test_category_case_is_merged_with_budget(self):
        self.run_cli("add", "5", "  Groceries ", "--date", "2026-10-02")
        self.add("5", "groceries", "2026-10-03")
        self.budget("GROCERIES", "200")
        r = self.report()
        self.assertEqual(
            r.out,
            HEADER
            + "groceries\t10.00\t200.00\t190.00\n"
            + "TOTAL\t10.00\t200.00\t190.00\n",
        )

    # Acceptance 2: OVER when spent > Budget; - when no Budget
    def test_spent_equal_to_budget_is_not_over(self):
        self.add("200", "groceries", "2026-10-02")
        self.budget("groceries", "200")
        r = self.report()
        self.assertIn("groceries\t200.00\t200.00\t0.00\n", r.out)
        self.assertNotIn("OVER", r.out)

    def test_one_cent_over_budget_is_over(self):
        self.add("200.01", "groceries", "2026-10-02")
        self.budget("groceries", "200")
        r = self.report()
        self.assertIn("groceries\t200.01\t200.00\t-0.01\tOVER\n", r.out)

    def test_zero_budget_with_spending_is_over(self):
        self.add("1", "groceries", "2026-10-02")
        self.budget("groceries", "0")
        r = self.report()
        self.assertIn("groceries\t1.00\t0.00\t-1.00\tOVER\n", r.out)

    def test_category_without_budget_is_never_over(self):
        self.add("9999", "transport", "2026-10-02")
        r = self.report()
        self.assertIn("transport\t9999.00\t-\t-\n", r.out)
        self.assertNotIn("OVER", r.out)

    # Acceptance 3: total line last
    def test_total_is_last_line(self):
        self.add("1", "zeta", "2026-10-02")
        self.budget("alpha", "5")
        lines = self.report().out.splitlines()
        self.assertEqual(lines[-1], "TOTAL\t1.00\t5.00\t5.00")
        self.assertEqual(sum(1 for ln in lines if ln.startswith("TOTAL")), 1)

    def test_total_spent_includes_categories_without_budget(self):
        self.add("10", "groceries", "2026-10-02")
        self.add("40", "transport", "2026-10-05")
        self.budget("groceries", "20")
        lines = self.report().out.splitlines()
        self.assertEqual(lines[-1], "TOTAL\t50.00\t20.00\t10.00")

    def test_total_is_dashes_when_no_category_has_a_budget(self):
        self.add("10", "groceries", "2026-10-02")
        self.add("40", "transport", "2026-10-05")
        self.assertEqual(self.report().out.splitlines()[-1], "TOTAL\t50.00\t-\t-")

    # Acceptance 4: only Expenses dated in the Month count
    def test_expenses_outside_month_are_not_counted(self):
        self.add("1", "groceries", "2026-09-30")
        self.add("2", "groceries", "2026-10-01")
        self.add("4", "groceries", "2026-10-31")
        self.add("8", "groceries", "2026-11-01")
        self.budget("groceries", "100")
        r = self.report()
        self.assertEqual(
            r.out,
            HEADER
            + "groceries\t6.00\t100.00\t94.00\n"
            + "TOTAL\t6.00\t100.00\t94.00\n",
        )

    def test_category_only_spent_outside_month_has_no_line(self):
        self.add("9", "groceries", "2026-11-01")
        self.add("40", "transport", "2026-10-05")
        r = self.report()
        self.assertEqual(
            r.out, HEADER + "transport\t40.00\t-\t-\n" + "TOTAL\t40.00\t-\t-\n"
        )

    def test_spec_exercise(self):
        self.add("250", "groceries", "2026-10-03")
        self.add("40", "transport", "2026-10-05")
        self.add("9", "groceries", "2026-11-01")
        self.budget("groceries", "200")
        r = self.report()
        self.assertEqual(r.code, 0, r.err)
        lines = r.out.splitlines()
        self.assertEqual(lines[0], "category\tspent\tbudget\tremaining")
        self.assertEqual(lines[1], "groceries\t250.00\t200.00\t-50.00\tOVER")
        self.assertEqual(lines[2], "transport\t40.00\t-\t-")
        self.assertTrue(lines[3].startswith("TOTAL\t290.00\t200.00\t-50.00"), lines[3])
        self.assertEqual(len(lines), 4)

    # Acceptance 5: empty Month, no Budgets
    def test_empty_month_prints_only_total(self):
        r = self.report("2030-01")
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.out, HEADER + "TOTAL\t0.00\t-\t-\n")
        self.assertEqual(r.err, "")

    def test_empty_month_with_budgets_lists_them_with_zero_spent(self):
        self.budget("groceries", "200")
        self.budget("rent", "800")
        r = self.report("2030-01")
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(
            r.out,
            HEADER
            + "groceries\t0.00\t200.00\t200.00\n"
            + "rent\t0.00\t800.00\t800.00\n"
            + "TOTAL\t0.00\t1000.00\t1000.00\n",
        )

    # Acceptance 6: bad Month
    def test_bad_month_13_rejected(self):
        self.assert_bad_month("2026-13")

    def test_bad_month_reversed_rejected(self):
        self.assert_bad_month("10-2026")

    def test_bad_month_short_month_rejected(self):
        self.assert_bad_month("2026-1")

    def test_bad_month_with_day_rejected(self):
        self.assert_bad_month("2026-10-01")

    def test_bad_month_error_names_the_value(self):
        r = self.run_cli("report", "--month", "2026-13")
        self.assertEqual(r.err, "ledger: error: bad month '2026-13'\n")

    def test_bad_month_does_not_change_stored_data(self):
        self.add("5", "groceries", "2026-10-02")
        before = self.run_cli("list").out
        self.run_cli("report", "--month", "2026-13")
        self.assertEqual(self.run_cli("list").out, before)
