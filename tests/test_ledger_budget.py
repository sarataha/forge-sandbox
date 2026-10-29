from tests.ledger_support import LedgerTestCase


class BudgetTest(LedgerTestCase):
    def assert_rejected(self, *argv):
        r = self.run_cli(*argv)
        self.assertEqual(r.code, 1, argv)
        self.assertEqual(r.out, "", argv)
        self.assertTrue(r.err.startswith("ledger: error: "), r.err)
        self.assertEqual(len(r.err.strip().splitlines()), 1, r.err)
        listed = self.run_cli("budget", "list")
        self.assertEqual(listed.code, 0)
        self.assertEqual(listed.out, "", argv)

    # Acceptance 1: set groceries 200 exits 0 and stores 20000 cents
    def test_set_exits_zero_and_prints_budget_line(self):
        r = self.run_cli("budget", "set", "groceries", "200")
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, "budget groceries 200.00\n")
        self.assertEqual(r.err, "")

    def test_set_stores_20000_cents(self):
        self.run_cli("budget", "set", "groceries", "200")
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t200.00\n")

    def test_set_decimal_amount_is_exact_cents(self):
        self.run_cli("budget", "set", "groceries", "12.5")
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t12.50\n")

    # Acceptance 2: same Category, any case, replaces
    def test_set_again_replaces_budget(self):
        self.run_cli("budget", "set", "groceries", "200")
        r = self.run_cli("budget", "set", "groceries", "300")
        self.assertEqual(r.code, 0)
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t300.00\n")

    def test_set_again_with_different_case_replaces_budget(self):
        self.run_cli("budget", "set", "groceries", "200")
        r = self.run_cli("budget", "set", "Groceries", "250")
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, "budget groceries 250.00\n")
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t250.00\n")

    def test_set_with_padded_upper_case_category_replaces_budget(self):
        self.run_cli("budget", "set", "groceries", "200")
        self.run_cli("budget", "set", "  GROCERIES ", "250")
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t250.00\n")

    # Acceptance 3: list prints each Category and Budget with two decimals
    def test_list_empty_prints_nothing(self):
        r = self.run_cli("budget", "list")
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, "")

    def test_list_prints_two_decimals_ordered_by_category(self):
        self.run_cli("budget", "set", "transport", "40")
        self.run_cli("budget", "set", "rent", "800.5")
        self.run_cli("budget", "set", "groceries", "200")
        r = self.run_cli("budget", "list")
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, "groceries\t200.00\nrent\t800.50\ntransport\t40.00\n")

    # Acceptance 4: invalid amounts exit 1, one-line error, store nothing
    def test_invalid_amounts_are_rejected_and_store_nothing(self):
        for bad in [
            "12.5.0",
            "1,000",
            ".5",
            "12.",
            "12.345",
            "+5",
            "1e3",
            "abc",
            "",
            "-3",
        ]:
            with self.subTest(amount=bad):
                self.assert_rejected("budget", "set", "groceries", bad)

    def test_invalid_amount_error_names_the_value(self):
        r = self.run_cli("budget", "set", "groceries", "12.5.0")
        self.assertEqual(r.err, "ledger: error: bad amount '12.5.0'\n")

    def test_amount_over_cap_is_rejected(self):
        self.assert_rejected("budget", "set", "groceries", "100000000.00")

    def test_invalid_amount_keeps_existing_budget(self):
        self.run_cli("budget", "set", "groceries", "200")
        self.assertEqual(self.run_cli("budget", "set", "groceries", "-3").code, 1)
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t200.00\n")

    def test_zero_amount_is_allowed(self):
        r = self.run_cli("budget", "set", "groceries", "0")
        self.assertEqual(r.code, 0)
        self.assertEqual(self.run_cli("budget", "list").out, "groceries\t0.00\n")

    def test_invalid_category_is_rejected(self):
        self.assert_rejected("budget", "set", "   ", "200")
        self.assert_rejected("budget", "set", "a\tb", "200")
