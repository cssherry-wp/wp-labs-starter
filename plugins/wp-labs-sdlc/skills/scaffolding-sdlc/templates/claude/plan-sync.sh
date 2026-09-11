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

# Missing lib = stale config dir with only one file installed. Fail quietly
# rather than spew a bash error into the user's session on every Stop.
# shellcheck source=./claude-lib.sh disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/claude-lib.sh" 2>/dev/null || exit 0

payload="$(cat)"
transcript="$(printf '%s' "$payload" | grep -o '"transcript_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*:[[:space:]]*"(.*)"/\1/')"
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

# No $PWD fallback: outside a git repo there is no project to sync into, and
# guessing the cwd would write plans into $HOME.
ROOT="$(project_root)" || exit 0
# Only sync into an adopted project, same guard as sidecar-sync.sh: in an
# unadopted tree these would land as untracked files someone may commit.
[ -L "$ROOT/.superpowers" ] || exit 0
DEST="$ROOT/.superpowers/02-plans"

# ponytail: the harness writes the plan path as a structured field on
# ExitPlanMode (input.planFilePath), not just prose, so grep that field name
# instead of scanning for path-shaped text (which also matches paths merely
# mentioned in web pages/files the session read). input.plan in the same
# block holds the full plan text too, so the file could be reconstructed
# without touching the filesystem at all, but that needs a real JSON parser
# for a multi-line escaped string, and jq isn't reliably on every machine, so
# path-plus-grep stays for now.
plans="$(grep -oE '"planFilePath"[[:space:]]*:[[:space:]]*"[^"]*"' "$transcript" | sed -E 's/.*"planFilePath"[[:space:]]*:[[:space:]]*"([^"]*)"/\1/' | sort -u)"
[ -n "$plans" ] || exit 0

# Resolved once: the only directory whose files are trusted as plans. Keyed off
# CLAUDE_CONFIG_DIR the same way settings.json invokes this script, so a
# non-default config dir isn't a permanent silent skip. Empty if it doesn't
# exist, in which case nothing can match and every candidate is rejected below.
PLANS_DIR="$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plans" 2>/dev/null && pwd -P)" || PLANS_DIR=""

copied=0
while IFS= read -r src; do
  # Provenance guard: the transcript contains arbitrary attacker-influenceable
  # text (web pages, file contents). Only files sitting directly in this user's
  # own plans directory are trusted, and never a symlink — cp follows one and
  # would publish whatever it points at to a shared remote.
  #
  # The parent is compared *resolved* (pwd -P), not as a string prefix. A string
  # prefix check passes for a symlinked intermediate directory
  # (~/.claude/plans/hop -> /etc), and neither a `..` substring test nor the
  # -L test on the final component catches that: cp would then exfiltrate an
  # arbitrary file to the shared sidecar remote.
  [ -n "$PLANS_DIR" ] || continue
  src_dir="$(cd "$(dirname "$src")" 2>/dev/null && pwd -P)" || continue
  [ "$src_dir" = "$PLANS_DIR" ] || continue
  [ -L "$src" ] && continue
  [ -f "$src" ] || continue
  slug="$(basename "$src" .md)"
  # Anchored to the dated-filename convention (YYYY-MM-DD-HHMM-<slug>.md), not
  # a bare *-$slug.md glob: unanchored, an existing ...-plan-sync.md would
  # satisfy the check for an unrelated plan whose slug is just "sync".
  existing="$(compgen -G "$DEST/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]-$slug.md" 2>/dev/null)"
  # Keep the latest: skip only if a same-content copy already exists. If the
  # plan was revised since, every existing file differs, so fall through and
  # add a new dated file rather than overwrite the old one (history is free).
  already_synced=0
  if [ -n "$existing" ]; then
    while IFS= read -r f; do
      cmp -s "$src" "$f" && { already_synced=1; break; }
    done <<< "$existing"
  fi
  [ "$already_synced" -eq 1 ] && continue
  # No `set -e`: report copy/date failures instead of printing OK for them.
  stamp="$(date -r "$src" '+%Y-%m-%d-%H%M')" || continue
  mkdir -p "$DEST"
  # ponytail: the stamp is minute-granular, so a plan revised twice inside one
  # minute overwrites its own earlier copy, contradicting the keep-every-version
  # intent above. A numeric suffix fixes it but then falls outside the
  # dated-name glob used for the already-synced check, so an unchanged plan
  # would re-copy forever. Fix both together (widen the glob to accept the
  # suffix) if losing a same-minute revision ever bites.
  if ! cp "$src" "$DEST/$stamp-$slug.md"; then
    echo "ERROR: failed to copy $src to .superpowers/02-plans" >&2
    continue
  fi
  copied=$((copied + 1))
done <<< "$plans"

[ "$copied" -gt 0 ] && echo "OK: copied $copied plan(s) to .superpowers/02-plans"
exit 0
