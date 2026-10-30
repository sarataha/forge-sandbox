import argparse
import importlib
import pkgutil
import sys

from sandbox.notes import commands
from sandbox.notes.store import NoteError


def register(top: argparse._SubParsersAction) -> None:
    notes = top.add_parser("notes", help="keep Notes")
    sub = notes.add_subparsers(dest="notes_cmd", required=True)
    for info in sorted(pkgutil.iter_modules(commands.__path__), key=lambda m: m.name):
        module = importlib.import_module(f"{commands.__name__}.{info.name}")
        before = set(sub.choices)
        module.register(sub)
        for name in set(sub.choices) - before:
            sub.choices[name].set_defaults(module=module)


def run(args: argparse.Namespace) -> int:
    try:
        return args.module.run(args)
    except NoteError as err:
        print(f"notes: error: {err}", file=sys.stderr)
        return 2
