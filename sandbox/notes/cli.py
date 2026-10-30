import argparse
import importlib
import os
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
    if sys.stdout is None:
        print("notes: error: stdout is closed", file=sys.stderr)
        return 2
    try:
        code = args.module.run(args)
        sys.stdout.flush()
        return code
    except NoteError as err:
        print(f"notes: error: {err}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # Python docs, "Note on SIGPIPE": point stdout at devnull so the
        # interpreter's exit-time flush does not fail again.
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            if devnull != sys.stdout.fileno():
                os.close(devnull)
        return 1
    except UnicodeEncodeError as err:
        print(f"notes: error: {err}", file=sys.stderr)
        return 2
    except OSError as err:
        print(f"notes: error: {err}", file=sys.stderr)
        return 2
