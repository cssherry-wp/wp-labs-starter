#!/usr/bin/env bash
# Copy the current session's Plan Mode plan into the team's convention
# location, .superpowers/02-plans/, if it isn't already there.
#
# Plan Mode (the ExitPlanMode flow) writes its plan to a global, per-user
# location — ~/.claude/plans/<slug>.md — not tied to any project. Unlike the
# writing-plans skill (which writes straight into .superpowers/02-plans/),
# nothing syncs a Plan Mode plan into the project. This script closes that
# gap, run from the Stop hook.
#
# We scope to THIS session's plan file (found in its transcript) rather than
# copying every file in ~/.claude/plans/, since that directory is shared
# across every project — copying all of it would leak other projects' plans
# into this one.
#
# Usage: plan-sync.sh   (reads the Stop hook's JSON payload from stdin)
set -uo pipefail

payload="$(cat)"
transcript="$(printf '%s' "$payload" | grep -o '"transcript_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*:[[:space:]]*"(.*)"/\1/')"
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

project_root() {
  local gcd root
  gcd="$(git rev-parse --git-common-dir 2>/dev/null)" || { echo "$PWD"; return; }
  root="$(cd "$gcd/.." 2>/dev/null && pwd -P)" || { echo "$PWD"; return; }
  echo "$root"
}

ROOT="$(project_root)"
[ -n "$ROOT" ] || exit 0
DEST="$ROOT/.superpowers/02-plans"

plans="$(grep -oE '[^"[:space:]]*/\.claude/plans/[^"/[:space:]]*\.md' "$transcript" | sort -u)"
[ -n "$plans" ] || exit 0

copied=0
while IFS= read -r src; do
  [ -f "$src" ] || continue
  slug="$(basename "$src" .md)"
  # Already synced if a dated file for this slug exists in the destination.
  if compgen -G "$DEST/*-$slug.md" > /dev/null 2>&1; then
    continue
  fi
  mkdir -p "$DEST"
  dst="$DEST/$(date -r "$src" '+%Y-%m-%d-%H%M')-$slug.md"
  cp "$src" "$dst"
  copied=$((copied + 1))
done <<< "$plans"

echo "OK: copied $copied plan(s) to .superpowers/02-plans"
