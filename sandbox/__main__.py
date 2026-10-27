import argparse
import sys


def greet(name: str, shout: bool = False) -> str:
    msg = f"hello, {name}"
    return msg.upper() if shout else msg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sandbox")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("greet")
    g.add_argument("name")
    g.add_argument("--shout", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "greet":
        print(greet(args.name, args.shout))
    return 0


if __name__ == "__main__":
    sys.exit(main())
