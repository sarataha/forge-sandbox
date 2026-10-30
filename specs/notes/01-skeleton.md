# notes 01: skeleton (add, list)

## Outcome
The owner can add notes and list them from the terminal.

## Acceptance
- [ ] `notes add "buy milk"` on a missing file prints `added 1`, exit 0; a second add prints `added 2`.
- [ ] `notes list` prints `<id>\t<text>` per note in id order; missing file → no output, exit 0.
- [ ] `notes add` with empty, whitespace-only, over-200-char, or tab/newline text → `notes: error: <msg>` on stderr, exit 2, file unchanged.
- [ ] A new module in `sandbox/notes/commands/` with `register` and `run` becomes a `notes` subcommand without editing `cli.py`.
- [ ] Existing `greet` and `ledger` commands still work (existing tests pass).

## Exercise
`SANDBOX_NOTES_FILE=$(mktemp -d)/n.json` then `python3 -m sandbox notes add "buy milk"`, `python3 -m sandbox notes list`, `python3 -m sandbox notes add ""; echo $?`.

## Out of scope
- `notes search` (slice 02), editing, deleting.

## Risk
none

## Interfaces
- Provides: `sandbox.notes.store.load`, `add`, `validate`, `NoteError`; command discovery in `sandbox.notes.cli`.

## Decisions
| Question | Answer |
|---|---|
| Notes file exists but is not valid JSON of the data model | `notes: error: cannot read <path>: <detail>`, exit 2, file left untouched. |
| Over-200 check | Applied after `strip()`, so surrounding whitespace does not count. |

Depends on: none
Owns: sandbox/__main__.py, sandbox/notes/__init__.py, sandbox/notes/cli.py, sandbox/notes/store.py, sandbox/notes/commands/__init__.py, sandbox/notes/commands/add.py, sandbox/notes/commands/listing.py, tests/test_notes_add_list.py
