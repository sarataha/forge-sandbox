from datetime import date

from sandbox.ledger.model import format_cents, make_expense


def handler(args, store, out) -> int:
    day = args.date if args.date is not None else date.today().isoformat()
    expense = make_expense(day, args.amount, args.category, args.note)
    (new_id,) = store.add([expense])
    out.write(
        f"added {new_id} {expense.date} {format_cents(expense.amount_cents)} {expense.category}\n"
    )
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("add", help="record an Expense")
    p.add_argument("amount")
    p.add_argument("category")
    p.add_argument("--date")
    p.add_argument("--note")
    p.set_defaults(handler=handler)
