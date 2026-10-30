# notes plan

Status: approved 2026-10-30

## Goal
Trial run for project-mode resume (setup-hardening proposal P7): a tiny two-slice CLI that the coordinator is deliberately killed and resumed during. The feature itself is throwaway.
Success measure: both slices merge into `dev` after two coordinator kills, with no duplicate worktree, branch or PR and no extra attempt counted.

## Journey check

```
J=$(mktemp -d); export SANDBOX_NOTES_FILE=$J/notes.json
python3 -m sandbox notes add "buy milk"                     # 01: prints "added 1"
python3 -m sandbox notes add "call the bank"               # 01: prints "added 2"
python3 -m sandbox notes list                              # 01: "1<TAB>buy milk" then "2<TAB>call the bank"
python3 -m sandbox notes search BANK                       # 02: "2<TAB>call the bank" only
python3 -m sandbox notes search zebra; test $? -eq 1       # 02: no output, exit 1
```

## Regression journeys
- `specs/ledger/plan.md` Journey check (ledger milestone, released 7f2f84c).

## Decisions
| Question | Answer |
|---|---|
| Real goal | Prove `run-project/RESUME.md` on a real run; the CLI is a vehicle. |
| Storage | One JSON file at `SANDBOX_NOTES_FILE`, default `./notes.json`: `{"notes": [{"id": 1, "text": "..."}]}`. Missing file = no notes. |
| Ids | Next id = highest existing id + 1, starting at 1. |
| Text | Non-empty after `strip()`, max 200 chars, no `\t`, `\r`, `\n`. Bad text: `notes: error: <msg>`, exit 2. |
| Search | Case-insensitive substring match on text (`casefold`). Matches printed like `list`; none → no output, exit 1. |
| Kill points | Kill 1: during 01 after its test commit is pushed, before the implementer finishes. Kill 2: during 02 while its PR is in review. |
| Run budget | Stop after 4 slice attempts (2 slices × 2). |

## Slices
| # | Slice | Depends on | Risk | Wave |
|---|---|---|---|---|
| 01 | 01-skeleton: `notes add`, `notes list`, JSON store, command discovery | none | none | 1 |
| 02 | 02-search: `notes search` | 01 | none | 2 |

## Run settings
- Parallel cap: 1
- Budget: stop after 4 slice attempts (owner told at 50% and 75%)
- Checkpoints: none
- Unanswered question mid-run: small, reversible, inside one slice → safest default, new Decisions row, listed in the release PR. Risky or shape-changing (auth, billing, license, customer data, migration, new dependency, shared interface or data model, spec contradiction, wrong acceptance test) → pause that slice and its dependents, ask the owner.

## Pre-mortem
- Resume starts a second worktree or branch for 01 → caught by the trial check after kill 1 (`git worktree list`, `git ls-remote`).
- Resume re-runs reviews already recorded, or skips a missing one → caught by the trial check after kill 2 (status file vs PR head).
- Store write from 01 breaks ledger → caught by Regression journeys.

## Out of scope
- Editing or deleting notes - deliberate: not needed to test resume.
- Release PR to `main` - deferred: owner decides after the trial.
