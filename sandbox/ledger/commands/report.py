import os

from sandbox.billing.detailed import render_detailed
from sandbox.billing.license import check_license
from sandbox.ledger.model import parse_month
from sandbox.ledger.report import build_report, render_report


def report_handler(args, store, out) -> int:
    month = parse_month(args.month)
    if args.detailed:
        check_license(os.environ.get("SANDBOX_LICENSE_KEY"))
        out.write(render_detailed(store, month))
    else:
        out.write(render_report(build_report(store, month)))
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("report", help="spending per Category against Budgets")
    p.add_argument("--month", required=True, metavar="YYYY-MM")
    p.add_argument(
        "--detailed",
        action="store_true",
        help="also list Expenses (needs a license key)",
    )
    p.set_defaults(handler=report_handler)
