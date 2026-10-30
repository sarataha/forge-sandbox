from sandbox.ledger.model import format_cents, parse_amount, parse_category


def set_handler(args, store, out) -> int:
    category = parse_category(args.category)
    cents = parse_amount(args.amount, allow_zero=True)
    store.set_budget(category, cents)
    out.write(f"budget {category} {format_cents(cents)}\n")
    return 0


def list_handler(args, store, out) -> int:
    for category, cents in sorted(store.budgets().items()):
        out.write(f"{category}\t{format_cents(cents)}\n")
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("budget", help="set or list Budgets")
    sub = p.add_subparsers(dest="budget_cmd", required=True)
    s = sub.add_parser("set", help="set the Budget for a Category")
    s.add_argument("category")
    s.add_argument("amount")
    s.set_defaults(handler=set_handler)
    ls = sub.add_parser("list", help="list Budgets")
    ls.set_defaults(handler=list_handler)
