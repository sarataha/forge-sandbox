from sandbox.ledger.model import format_cents, parse_month


def handler(args, store, out) -> int:
    month = parse_month(args.month) if args.month is not None else None
    for e in store.expenses(month):
        out.write(f"{e.date}\t{format_cents(e.amount_cents)}\t{e.category}\t{e.note}\n")
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("list", help="list Expenses")
    p.add_argument("--month")
    p.set_defaults(handler=handler)
