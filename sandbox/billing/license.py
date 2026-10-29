import hmac
import re

from sandbox.ledger.model import LedgerError

TEST_SECRET = b"forge-sandbox-ledger-test-secret-v1"  # gitleaks:allow

_KEY_RE = re.compile(r"LEDGER1-([a-z0-9]{1,32})-([0-9a-f]{64})")


class LicenseError(LedgerError):
    exit_code = 3

    def message_line(self) -> str:
        return f"ledger: upgrade: {self}"


def _mac(subject: str) -> str:
    return hmac.new(
        TEST_SECRET, f"LEDGER1-{subject}".encode("ascii"), "sha256"
    ).hexdigest()


def issue_key(subject: str) -> str:
    return f"LEDGER1-{subject}-{_mac(subject)}"


def check_license(key: str | None) -> None:
    if key is None or not key.strip():
        raise LicenseError("--detailed needs a license key in SANDBOX_LICENSE_KEY")
    m = _KEY_RE.fullmatch(key.strip())
    if m is None or not hmac.compare_digest(_mac(m.group(1)), m.group(2)):
        raise LicenseError("SANDBOX_LICENSE_KEY is not a valid license key")
