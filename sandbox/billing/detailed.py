from sandbox.ledger.model import format_cents
from sandbox.ledger.report import build_report, render_report


def _line(e) -> str:
    return f"{e.date}\t{format_cents(e.amount_cents)}\t{e.category}\t{e.note}\n"


def render_detailed(store, month: str) -> str:
    expenses = store.expenses(month)
    out = render_report(build_report(store, month)) + "\n"
    for category in sorted({e.category for e in expenses}):
        out += f"## {category}\n"
        out += "".join(_line(e) for e in expenses if e.category == category)
    out += "## top 3\n"
    top = sorted(expenses, key=lambda e: (-e.amount_cents, e.date, e.id))[:3]
    return out + "".join(_line(e) for e in top)
