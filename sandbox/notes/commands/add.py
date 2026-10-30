from sandbox.notes import store


def register(sub) -> None:
    p = sub.add_parser("add", help="add a Note")
    p.add_argument("text")


def run(args) -> int:
    print(f"added {store.add(args.text)}")
    return 0
