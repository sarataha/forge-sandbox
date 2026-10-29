import argparse
import importlib
import pkgutil
import sqlite3
import sys

from sandbox.ledger import commands
from sandbox.ledger.model import LedgerError
from sandbox.ledger.store import open_store


def register(top: argparse._SubParsersAction) -> None:
    ledger = top.add_parser("ledger", help="track Expenses")
    sub = ledger.add_subparsers(dest="ledger_cmd", required=True)
    names = sorted(m.name for m in pkgutil.iter_modules(commands.__path__))
    for name in names:
        importlib.import_module(f"{commands.__name__}.{name}").register(sub)


def run(args: argparse.Namespace) -> int:
    try:
        with open_store() as store:
            return args.handler(args, store, sys.stdout)
    except LedgerError as err:
        print(err.message_line(), file=sys.stderr)
        return err.exit_code
    except sqlite3.Error as err:
        print(f"ledger: error: database: {err}", file=sys.stderr)
        return 1
