# notes 02: search

## Outcome
The owner can find notes containing a word.

## Acceptance
- [ ] `notes search BANK` prints every note whose text contains `bank` in any case, as `<id>\t<text>` in id order, exit 0.
- [ ] No match → no output, exit 1.
- [ ] Empty or whitespace-only word → `notes: error: <msg>`, exit 2.
- [ ] `cli.py` is not edited (the command is found by discovery).

## Exercise
After two `notes add` calls (01 Exercise), `python3 -m sandbox notes search BANK` and `python3 -m sandbox notes search zebra; echo $?`.

## Out of scope
- Regex, word boundaries, ranking.

## Risk
none

## Interfaces
- Uses: `sandbox.notes.store.load` (from 01-skeleton), command discovery (from 01-skeleton)
- Provides: `notes search <word>`

Depends on: 01-skeleton
Owns: sandbox/notes/commands/search.py, tests/test_notes_search.py
