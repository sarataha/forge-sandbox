from sandbox.ledger.model import parse_month
from sandbox.ledger.report import build_report, render_report


def report_handler(args, store, out) -> int:
    month = parse_month(args.month)
    out.write(render_report(build_report(store, month)))
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("report", help="spending per Category against Budgets")
    p.add_argument("--month", required=True, metavar="YYYY-MM")
    p.set_defaults(handler=report_handler)
