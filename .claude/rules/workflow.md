# ~/gh: personal projects

GitHub user `sarataha`. Tracker: GitHub Issues. Ignore `ideas/`.

## Flow

Human shapes issue + system. Agents do the rest.

`/shape <idea>` → `/ship <issue>` → `/guard <pr>` → `/land <pr>`. New repo: `/new-project`.

## Rules (all repos)

- Read the repo's `AGENTS.md` first. Repo rules override this file.
- One issue = one vertical slice = one PR. Branch off `main`; never push to `main`.
- Exercise before PR: run the changed path for real, write what you saw in `## Exercised`. Tests passing is not exercising.
- Run the repo's lint + tests locally before every push.
- Author never approves own work: reviews and risk verdicts run in fresh-context subagents.
- Never merge except via `/land` rules. Never auto-merge license, billing, auth, or customer-data access code.
- Never weaken, skip, or delete a test to go green. Fix code or stop and say why.
- Deps: stdlib first, else maintained upstream at latest stable. Pin GitHub Actions to SHAs.
- Tests + fixtures use seeded fake data only. No real customer data, emails, or keys anywhere in repo, logs, or PRs.
- Secrets live in env / GitHub secrets, never in code, issues, or PR text.
- OSS-facing text (PR, commit, README, release notes) never mentions employer or internal use.
- Commit body length matches change size. Conventional Commits.
- Stuck after 2 real attempts on the same failure: stop, comment on issue/PR with what was tried.

## Drift → guardrail

When an agent drifts, fix it where it would have been prevented:
- repo-specific → that repo's `AGENTS.md` or CI check
- all repos → this file or the relevant skill in `~/.claude/skills/`
Prefer a CI check over prose when the rule is mechanical.
