import argparse
import importlib
import os
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
            code = args.handler(args, store, sys.stdout)
            sys.stdout.flush()
            return code
    except LedgerError as err:
        print(err.message_line(), file=sys.stderr)
        return err.exit_code
    except sqlite3.Error as err:
        print(f"ledger: error: database: {err}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Python docs, "Note on SIGPIPE": point stdout at devnull so the
        # interpreter's exit-time flush does not fail again.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)
        return 1
    except OSError as err:
        print(f"ledger: error: {err}", file=sys.stderr)
        return 1
