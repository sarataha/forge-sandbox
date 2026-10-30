from sandbox.notes import store


def register(sub) -> None:
    p = sub.add_parser("search", help="find Notes containing a word")
    p.add_argument("word")


def run(args) -> int:
    word = args.word.strip()
    if not word:
        raise store.NoteError("word is empty")
    needle = word.casefold()
    found = False
    for note in sorted(store.load(), key=lambda n: n["id"]):
        if needle in note["text"].casefold():
            print(f"{note['id']}\t{note['text']}")
            found = True
    return 0 if found else 1
