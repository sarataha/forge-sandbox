# forge-sandbox
Throwaway CLI for testing the ship/guard/land agent workflow. Audience: me. Paid (private).

## Commands
setup: none (stdlib only)   lint: `uvx ruff check .`   test: `python3 -m unittest -v`   run: `python3 -m sandbox greet <name>`   seed: `python3 scripts/seed.py`

## Exercise
Run `python3 -m sandbox <subcommand> ...` and paste the exact output.

## Conventions
Stdlib only; no third-party runtime deps.

## Boundaries
- Sensitive paths (always human review): `sandbox/auth/`, `sandbox/billing/`
- Test data: seeded fake data only (`python3 scripts/seed.py`, fixed seed). Never real customer data.

Auto-merge: low-risk
