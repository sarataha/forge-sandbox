import csv
import json

from sandbox.ledger.model import CSV_COLUMNS, format_cents


def _write_csv(expenses, out) -> None:
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for e in expenses:
        writer.writerow([e.date, format_cents(e.amount_cents), e.category, e.note])


def _write_json(expenses, out) -> None:
    doc = {
        "expenses": [
            {
                "amount_cents": e.amount_cents,
                "category": e.category,
                "date": e.date,
                "note": e.note,
            }
            for e in expenses
        ],
        "format": "ledger-export",
        "version": 1,
    }
    print(json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True), file=out)


def handler(args, store, out) -> int:
    expenses = store.expenses()
    if args.format == "json":
        _write_json(expenses, out)
    else:
        _write_csv(expenses, out)
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("export", help="write all Expenses as CSV or JSON")
    p.add_argument("--format", choices=("csv", "json"), default="csv")
    p.set_defaults(handler=handler)
