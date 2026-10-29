from dataclasses import dataclass

from sandbox.ledger.model import format_cents


@dataclass(frozen=True)
class ReportRow:
    category: str
    spent_cents: int
    budget_cents: int | None

    @property
    def remaining_cents(self) -> int | None:
        if self.budget_cents is None:
            return None
        return self.budget_cents - self.spent_cents

    @property
    def over(self) -> bool:
        return self.budget_cents is not None and self.spent_cents > self.budget_cents


@dataclass(frozen=True)
class Report:
    month: str
    rows: list[ReportRow]
    spent_cents: int


def build_report(store, month: str) -> Report:
    spent: dict[str, int] = {}
    total = 0
    for e in store.expenses(month):
        spent[e.category] = spent.get(e.category, 0) + e.amount_cents
        total += e.amount_cents
    budgets = store.budgets()
    rows = [
        ReportRow(c, spent.get(c, 0), budgets.get(c))
        for c in sorted(spent.keys() | budgets.keys())
    ]
    return Report(month, rows, total)


def _money(cents: int | None) -> str:
    return "-" if cents is None else format_cents(cents)


def render_report(report: Report) -> str:
    lines = ["category\tspent\tbudget\tremaining"]
    for r in report.rows:
        line = (
            f"{r.category}\t{format_cents(r.spent_cents)}"
            f"\t{_money(r.budget_cents)}\t{_money(r.remaining_cents)}"
        )
        lines.append(line + "\tOVER" if r.over else line)
    budgeted = [r for r in report.rows if r.budget_cents is not None]
    budget = sum(r.budget_cents for r in budgeted) if budgeted else None
    remaining = sum(r.remaining_cents for r in budgeted) if budgeted else None
    lines.append(
        f"TOTAL\t{format_cents(report.spent_cents)}\t{_money(budget)}\t{_money(remaining)}"
    )
    return "\n".join(lines) + "\n"
