from sandbox.notes import store


def register(sub) -> None:
    sub.add_parser("list", help="list Notes")


def run(args) -> int:
    for note in sorted(store.load(), key=lambda n: n["id"]):
        print(f"{note['id']}\t{note['text']}")
    return 0
