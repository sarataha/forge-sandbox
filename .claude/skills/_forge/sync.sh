#!/usr/bin/env bash
# Copy the agent kit into a repo so cloud runs (which only see committed files) have it.
# Usage: sync.sh <repo-dir>. Leaves changes uncommitted for review.
set -euo pipefail
dest=$1
src=$(cd "$(dirname "$0")/.." && pwd)   # ~/.claude/skills
mkdir -p "$dest/.claude/skills" "$dest/.claude/rules"
for s in ship guard land _forge; do
  rm -rf "${dest:?}/.claude/skills/$s"
  cp -R "$src/$s" "$dest/.claude/skills/$s"
done
cp "$src/_forge/workflow.md" "$dest/.claude/rules/workflow.md"

# Cloud runs read the repo's .claude/settings.json: no claude.ai session link in commits/PRs.
s="$dest/.claude/settings.json"
[ -f "$s" ] || echo '{}' > "$s"
tmp=$(mktemp)
jq '.attribution.sessionUrl = false' "$s" > "$tmp" && mv "$tmp" "$s"
git -C "$dest" status --short .claude
