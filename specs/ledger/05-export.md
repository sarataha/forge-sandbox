# Export to CSV or JSON

## Outcome
The owner can export every Expense with `sandbox ledger export --format csv|json`, and a CSV export re-imports into an empty ledger unchanged.

## Acceptance
- [ ] `export --format csv` writes the pinned ledger CSV format to stdout, oldest date first.
- [ ] `export --format json` writes the pinned JSON shape to stdout.
- [ ] Importing a CSV export into an empty ledger gives the same Expenses (round trip), checked by a test through the CLI.
- [ ] Notes containing commas, quotes and newlines survive the CSV round trip.
- [ ] An empty ledger exports a header-only CSV and `[]` JSON, exit 0.

## Exercise
```
export SANDBOX_LEDGER_DB=$(mktemp -d)/ledger.db
python3 -m sandbox ledger add 12.50 groceries --date 2026-10-03 --note 'market, "fresh"'
python3 -m sandbox ledger export --format csv
python3 -m sandbox ledger export --format json
```

## Out of scope
- Writing to a file path (stdout only); other formats.

## Risk
none

## Interfaces
- Uses: `CSV_COLUMNS`, `format_cents`, `Store.expenses` (01), `ledger import` for the round-trip test (03)
- Provides: `ledger export --format csv|json` (architecture.md: ledger.commands.export, CSV, JSON export)

Depends on: 03
Owns: sandbox/ledger/commands/export.py, tests/test_ledger_export.py
