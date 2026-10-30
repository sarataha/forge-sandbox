# notes architecture

## Glossary
**Note**: one line of text with an integer id, stored in the notes file. _Avoid_: memo, entry.

## Stack
| Choice | Version | Why | Source (checked 2026-10-30) |
|---|---|---|---|
| Python stdlib (`argparse`, `json`, `pkgutil`) | repo's Python 3, no new dependency | AGENTS.md: stdlib only | `AGENTS.md` on `dev` |

## Global constraints
- Stdlib only. Tests use a temp `SANDBOX_NOTES_FILE`, never `./notes.json`.
- Errors print one line `notes: error: <msg>` to stderr; exit 2 for bad input, 1 for "nothing found".
- Writes replace the file atomically (write a temp file in the same folder, then `os.replace`).

## Modules
### sandbox.notes.store
- Interface: `load(path: str | None = None) -> list[dict]`, `add(text: str, path: str | None = None) -> int` (returns the new id). `path` `None` → `os.environ.get("SANDBOX_NOTES_FILE") or "./notes.json"`. `validate(text: str) -> str` returns the stripped text or raises `NoteError(msg)`.
- Owns: `sandbox/notes/store.py`
- Test seam: through the CLI (`sandbox.__main__.main([...])`) with a temp `SANDBOX_NOTES_FILE`.
- Uses: none

### sandbox.notes.cli
- Interface: `register(sub)` adds the `notes` parser and one subparser per module in `sandbox.notes.commands` (each module defines `register(sub)` and `run(args) -> int`, found with `pkgutil.iter_modules`); `run(args) -> int` calls the chosen module, catches `NoteError` → error line, exit 2.
- Owns: `sandbox/notes/__init__.py`, `sandbox/notes/cli.py`, `sandbox/notes/commands/__init__.py`, `sandbox/notes/commands/add.py`, `sandbox/notes/commands/listing.py`
- Test seam: `sandbox.__main__.main(["notes", ...])`, capturing stdout/stderr.
- Uses: `sandbox.notes.store`

### sandbox.notes.commands.search
- Interface: `register(sub)`, `run(args) -> int` for `notes search <word>`.
- Owns: `sandbox/notes/commands/search.py`
- Test seam: same as cli.
- Uses: `sandbox.notes.store.load`

## Data model
`{"notes": [{"id": <int>, "text": <str>}]}`, ids unique, list in insertion order. Output line: `<id>\t<text>`.

## Shared files
`sandbox/__main__.py` (01 adds `notes` registration and dispatch).

## Review focus
- Missing or empty notes file → `list` prints nothing, exit 0 (pinned by 01)
- Text with tab or newline → error, exit 2, file unchanged (pinned by 01)
- Search word differing only in case → match (pinned by 02)
