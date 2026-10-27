import argparse
import sys


def greet(name: str) -> str:
    return f"hello, {name}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sandbox")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("greet")
    g.add_argument("name")
    args = parser.parse_args(argv)
    if args.cmd == "greet":
        print(greet(args.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
