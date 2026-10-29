import hashlib
import hmac
import re
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.ledger_support import LedgerTestCase

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "scripts" / "seed.py"
SECRET = b"forge-sandbox-ledger-test-secret-v1"
KEY_RE = r"LEDGER1-([a-z0-9]{1,32})-([0-9a-f]{64})"
# sha256 of `python3 scripts/seed.py` stdout before slice 06
SEED_SHA256 = "8e491d1590fff83cd65b4961a9e93b7f048a5ba6832466f9295f95efd8b01f34"

MSG_MISSING = "ledger: upgrade: --detailed needs a license key in SANDBOX_LICENSE_KEY\n"
MSG_INVALID = "ledger: upgrade: SANDBOX_LICENSE_KEY is not a valid license key\n"

PLAIN_REPORT = (
    "category\tspent\tbudget\tremaining\n"
    "groceries\t12.50\t-\t-\n"
    "transport\t40.00\t-\t-\n"
    "TOTAL\t52.50\t-\t-\n"
)
DETAIL_BLOCK = (
    "\n"
    "## groceries\n"
    "2026-10-03\t12.50\tgroceries\tmarket\n"
    "## transport\n"
    "2026-10-05\t40.00\ttransport\t\n"
    "## top 3\n"
    "2026-10-05\t40.00\ttransport\t\n"
    "2026-10-03\t12.50\tgroceries\tmarket\n"
)


def valid_key():
    from sandbox.billing.license import issue_key

    return issue_key("owner")


class DetailedTestCase(LedgerTestCase):
    def add(self, amount, category, date, note=None):
        argv = ["add", amount, category, "--date", date]
        if note is not None:
            argv += ["--note", note]
        r = self.run_cli(*argv)
        self.assertEqual(r.code, 0, r.err)

    def seed_two(self):
        self.add("12.50", "groceries", "2026-10-03", "market")
        self.add("40", "transport", "2026-10-05")

    def detailed(self, month="2026-10", key=None):
        return self.run_cli(
            "report",
            "--month",
            month,
            "--detailed",
            env={"SANDBOX_LICENSE_KEY": key if key is not None else valid_key()},
        )

    def assert_upgrade(self, r, message=None):
        self.assertEqual(r.code, 3, r.err)
        self.assertEqual(r.out, "")
        self.assertTrue(r.err.startswith("ledger: upgrade: "), r.err)
        self.assertEqual(len(r.err.strip().splitlines()), 1, r.err)
        if message is not None:
            self.assertEqual(r.err, message)


class DetailedOutputTest(DetailedTestCase):
    # Acceptance 1: normal Report, then each Category's Expenses, then top 3
    def test_valid_key_prints_report_then_sections_then_top_3(self):
        self.seed_two()
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.err, "")
        self.assertEqual(r.out, PLAIN_REPORT + DETAIL_BLOCK)

    # Acceptance 1: a Budget-only Category has a Report row but no section
    def test_budget_only_category_has_no_section(self):
        self.seed_two()
        self.assertEqual(self.run_cli("budget", "set", "rent", "800").code, 0)
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        self.assertIn("rent\t0.00\t800.00\t800.00\n", r.out)
        self.assertNotIn("## rent", r.out)
        self.assertIn("## groceries\n", r.out)

    # Acceptance 1: sections ordered by Category name, lines by (date, id)
    def test_sections_by_category_and_lines_by_date_then_id(self):
        self.add("5", "zeta", "2026-10-09", "late")
        self.add("6", "alpha", "2026-10-04", "second-added")
        self.add("7", "alpha", "2026-10-02", "earlier-date")
        self.add("8", "alpha", "2026-10-04", "third-added")
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        detail = r.out[r.out.index("\n## alpha") :]
        self.assertEqual(
            detail,
            "\n## alpha\n"
            "2026-10-02\t7.00\talpha\tearlier-date\n"
            "2026-10-04\t6.00\talpha\tsecond-added\n"
            "2026-10-04\t8.00\talpha\tthird-added\n"
            "## zeta\n"
            "2026-10-09\t5.00\tzeta\tlate\n"
            "## top 3\n"
            "2026-10-04\t8.00\talpha\tthird-added\n"
            "2026-10-02\t7.00\talpha\tearlier-date\n"
            "2026-10-04\t6.00\talpha\tsecond-added\n",
        )

    # Acceptance 1: only the 3 largest, ties by date then id
    def test_top_3_limits_to_three_and_breaks_ties_by_date_then_id(self):
        self.add("10", "a", "2026-10-09", "nine")
        self.add("10", "a", "2026-10-02", "two-first")
        self.add("10", "a", "2026-10-02", "two-second")
        self.add("5", "a", "2026-10-01", "small")
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        top = r.out[r.out.index("## top 3\n") :]
        self.assertEqual(
            top,
            "## top 3\n"
            "2026-10-02\t10.00\ta\ttwo-first\n"
            "2026-10-02\t10.00\ta\ttwo-second\n"
            "2026-10-09\t10.00\ta\tnine\n",
        )

    # Acceptance 1: fewer than 3 Expenses lists what exists
    def test_top_3_with_one_expense(self):
        self.add("12.50", "groceries", "2026-10-03", "market")
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(
            r.out,
            "category\tspent\tbudget\tremaining\n"
            "groceries\t12.50\t-\t-\n"
            "TOTAL\t12.50\t-\t-\n"
            "\n"
            "## groceries\n"
            "2026-10-03\t12.50\tgroceries\tmarket\n"
            "## top 3\n"
            "2026-10-03\t12.50\tgroceries\tmarket\n",
        )

    # Acceptance 1: the top 3 header is always printed
    def test_empty_month_still_prints_top_3_header(self):
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(
            r.out,
            "category\tspent\tbudget\tremaining\nTOTAL\t0.00\t-\t-\n\n## top 3\n",
        )

    # Acceptance 1: detail covers only the requested Month
    def test_other_months_are_not_in_detail(self):
        self.seed_two()
        self.add("99", "groceries", "2026-09-30", "september")
        self.add("98", "groceries", "2026-11-01", "november")
        r = self.detailed()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.out, PLAIN_REPORT + DETAIL_BLOCK)

    # Review focus: valid key with surrounding whitespace/newline is accepted
    def test_key_with_surrounding_whitespace_is_accepted(self):
        self.seed_two()
        r = self.detailed(key="  " + valid_key() + "\n")
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.out, PLAIN_REPORT + DETAIL_BLOCK)


class DetailedRefusalTest(DetailedTestCase):
    # Acceptance 2: no key
    def test_no_key_exits_3_with_upgrade_message(self):
        self.seed_two()
        r = self.run_cli("report", "--month", "2026-10", "--detailed")
        self.assert_upgrade(r, MSG_MISSING)

    # Acceptance 2: empty key is the same as missing
    def test_empty_key_exits_3_with_missing_message(self):
        self.seed_two()
        r = self.detailed(key="")
        self.assert_upgrade(r, MSG_MISSING)

    # Acceptance 2: whitespace-only key is invalid (never prints stdout)
    def test_whitespace_key_exits_3(self):
        self.seed_two()
        self.assert_upgrade(self.detailed(key="   \n"))

    # Acceptance 2: tampered keys
    def test_tampered_keys_exit_3_with_invalid_message(self):
        from sandbox.billing.license import issue_key

        self.seed_two()
        key = issue_key("owner")
        subject_mac = key.split("-", 2)[2]
        other_mac = issue_key("other").split("-", 2)[2]
        flipped = key[:-1] + ("0" if key[-1] != "0" else "1")
        cases = {
            "wrong mac": flipped,
            "upper-case mac": "LEDGER1-owner-" + subject_mac.upper(),
            "mac of another subject": "LEDGER1-owner-" + other_mac,
            "truncated": key[:-1],
            "no mac": "LEDGER1-owner",
            "garbage": "not-a-key",
            "wrong prefix": "LEDGER2-owner-" + subject_mac,
        }
        for name, bad in cases.items():
            with self.subTest(name):
                self.assert_upgrade(self.detailed(key=bad), MSG_INVALID)

    # Acceptance 2: the plain Report is unaffected
    def test_plain_report_unaffected_without_key(self):
        self.seed_two()
        r = self.run_cli("report", "--month", "2026-10")
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.err, "")
        self.assertEqual(r.out, PLAIN_REPORT)

    # Acceptance 2: a key does not change the plain Report either
    def test_plain_report_unaffected_with_key(self):
        self.seed_two()
        r = self.run_cli(
            "report", "--month", "2026-10", env={"SANDBOX_LICENSE_KEY": valid_key()}
        )
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.out, PLAIN_REPORT)

    # Acceptance 2: invalid key with plain report is not checked
    def test_plain_report_ignores_invalid_key(self):
        self.seed_two()
        r = self.run_cli(
            "report", "--month", "2026-10", env={"SANDBOX_LICENSE_KEY": "bogus"}
        )
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.out, PLAIN_REPORT)


class LicenseKeyTest(unittest.TestCase):
    # Acceptance 4: key is LEDGER1-<subject>-<hmac sha256 of "LEDGER1-<subject>">
    def test_issue_key_format_and_mac(self):
        from sandbox.billing.license import issue_key

        key = issue_key("owner")
        m = re.fullmatch(KEY_RE, key)
        self.assertIsNotNone(m, key)
        self.assertEqual(m.group(1), "owner")
        expected = hmac.new(SECRET, b"LEDGER1-owner", hashlib.sha256).hexdigest()
        self.assertEqual(m.group(2), expected)

    # Acceptance 4: a key built by hand from the fixed secret is accepted
    def test_check_license_accepts_hand_built_key(self):
        from sandbox.billing.license import check_license

        mac = hmac.new(SECRET, b"LEDGER1-acme42", hashlib.sha256).hexdigest()
        self.assertIsNone(check_license("LEDGER1-acme42-" + mac))
        self.assertIsNone(check_license("\n LEDGER1-acme42-" + mac + " \n"))

    # Acceptance 2, 4: missing or invalid keys raise LicenseError, exit code 3
    def test_check_license_rejects_bad_keys(self):
        from sandbox.billing.license import LicenseError, check_license
        from sandbox.ledger.model import LedgerError

        good = hmac.new(SECRET, b"LEDGER1-owner", hashlib.sha256).hexdigest()
        bad = [
            None,
            "",
            "   ",
            "LEDGER1-owner-" + "0" * 64,
            "LEDGER1-owner-" + good.upper(),
            "LEDGER1-owner-" + good[:-1],
            "LEDGER1-owner-" + good + "0",
            "LEDGER1--" + good,
            "LEDGER1-Owner-" + good,
            "LEDGER1-" + "a" * 33 + "-" + good,
            "LEDGER1-owner-" + good + "\nextra",
        ]
        for key in bad:
            with self.subTest(key=key):
                with self.assertRaises(LicenseError) as ctx:
                    check_license(key)
                self.assertIsInstance(ctx.exception, LedgerError)
                self.assertEqual(ctx.exception.exit_code, 3)

    # Acceptance 4: the check never touches the network
    def test_check_is_offline(self):
        from sandbox.billing.license import check_license, issue_key

        def no_network(*args, **kwargs):
            raise AssertionError("network used")

        with (
            patch.object(socket, "socket", no_network),
            patch.object(socket, "create_connection", no_network),
            patch.object(socket, "getaddrinfo", no_network),
        ):
            check_license(issue_key("owner"))

    # Acceptance 4: the whole --detailed run is offline
    def test_detailed_run_is_offline(self):
        case = DetailedOutputTest(
            "test_valid_key_prints_report_then_sections_then_top_3"
        )
        case.setUp()
        try:
            case.seed_two()

            def no_network(*args, **kwargs):
                raise AssertionError("network used")

            with (
                patch.object(socket, "socket", no_network),
                patch.object(socket, "create_connection", no_network),
                patch.object(socket, "getaddrinfo", no_network),
            ):
                r = case.detailed()
            case.assertEqual(r.code, 0, r.err)
        finally:
            case.doCleanups()


class SeedScriptTest(unittest.TestCase):
    def run_seed(self, *args):
        return subprocess.run(
            [sys.executable, str(SEED), *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )

    # Acceptance 3: --license prints a valid key and a newline
    def test_seed_license_prints_valid_key(self):
        from sandbox.billing.license import check_license

        p = self.run_seed("--license")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertRegex(p.stdout, KEY_RE + r"\n")
        self.assertEqual(p.stdout.count("\n"), 1)
        self.assertIsNone(check_license(p.stdout.strip()))

    # Acceptance 3: works from another working directory too
    def test_seed_license_works_outside_repo_root(self):
        from sandbox.billing.license import check_license

        p = subprocess.run(
            [sys.executable, str(SEED), "--license"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(Path(sys.executable).parent),
            timeout=30,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIsNone(check_license(p.stdout.strip()))

    # Acceptance 3: no arguments, same users JSON as before
    def test_seed_without_args_prints_same_users_json(self):
        import json

        p = self.run_seed()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("LEDGER1", p.stdout)
        users = json.loads(p.stdout)
        self.assertEqual([u["id"] for u in users], list(range(10)))
        self.assertEqual(
            users[0], {"id": 0, "name": "margaret", "email": "user0@example.com"}
        )
        self.assertEqual(
            users[1], {"id": 1, "name": "ada", "email": "user1@example.com"}
        )
        self.assertEqual(hashlib.sha256(p.stdout.encode()).hexdigest(), SEED_SHA256)


if __name__ == "__main__":
    unittest.main()
