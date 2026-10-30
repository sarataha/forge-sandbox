import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

CSV_COLUMNS: tuple[str, ...] = ("date", "amount", "category", "note")
MAX_CENTS = 9_999_999_999


def _bad_text(value: str) -> bool:
    return any(unicodedata.category(c) in ("Cc", "Zl", "Zp") for c in value)


def _q(text: str) -> str:
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in text)


class LedgerError(Exception):
    exit_code = 1

    def message_line(self) -> str:
        return f"ledger: error: {self}"


class ValidationError(LedgerError):
    pass


@dataclass(frozen=True)
class Expense:
    date: str
    amount_cents: int
    category: str
    note: str = ""
    id: int | None = field(default=None, compare=False)


def parse_amount(text: str, *, allow_zero: bool = False) -> int:
    value = text.strip()
    if not re.fullmatch(r"[0-9]+(\.[0-9]{1,2})?", value):
        raise ValidationError(f"bad amount '{_q(text)}'")
    whole, _, frac = value.partition(".")
    if len(whole.lstrip("0")) > len(str(MAX_CENTS // 100)):
        raise ValidationError(f"bad amount '{_q(text)}'")
    cents = int(whole) * 100 + int(frac.ljust(2, "0") or "0")
    if cents > MAX_CENTS or cents < (0 if allow_zero else 1):
        raise ValidationError(f"bad amount '{_q(text)}'")
    return cents


def format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"


def parse_date(text: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValidationError(f"bad date '{_q(text)}'")
    try:
        date.fromisoformat(text)
    except ValueError:
        raise ValidationError(f"bad date '{_q(text)}'") from None
    return text


def parse_month(text: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", text):
        raise ValidationError(f"bad month '{_q(text)}'")
    return text


def parse_category(text: str) -> str:
    value = text.strip().casefold()
    if not value:
        raise ValidationError("empty category")
    if _bad_text(value) or len(value) > 64:
        raise ValidationError(f"bad category '{_q(text)}'")
    return value


def parse_note(text: str | None) -> str:
    if text is None:
        return ""
    value = text.strip()
    if _bad_text(value) or len(value) > 200:
        raise ValidationError(f"bad note '{_q(text)}'")
    return value


def make_expense(d: str, amount: str, category: str, note: str | None) -> Expense:
    return Expense(
        date=parse_date(d),
        amount_cents=parse_amount(amount),
        category=parse_category(category),
        note=parse_note(note),
    )
