#!/usr/bin/env bash
# The single implementation of superpowers-sidecar git mechanics.
#
# Every caller — the SessionStart/Stop hooks in settings.json, and the
# superpowers-sidecar-init skill — goes through this script so the commit,
# push, and rebase-retry behaviour exists in exactly one place.
#
# A project is "adopted" when its .superpowers is a symlink into the sidecar
# clone. In any other project this exits 0 without output: not being adopted is
# the normal case, not an error, and hooks run in every project.
#
# Usage:
#   sidecar-sync.sh pull                # SessionStart: fast-forward the clone
#   sidecar-sync.sh push "<message>"    # commit everything + push, with retry
set -uo pipefail

SIDECAR_DIR="${SIDECAR_DIR:-$HOME/.superpowers-sidecar}"

# Not adopted (or no sidecar clone yet) -> silent no-op.
[ -L "$PWD/.superpowers" ] || exit 0
[ -d "$SIDECAR_DIR/.git" ] || exit 0

cmd="${1:-}"
case "$cmd" in
  pull)
    git -C "$SIDECAR_DIR" pull --rebase --quiet || {
      git -C "$SIDECAR_DIR" rebase --abort 2>/dev/null
      echo "WARNING: superpowers-sidecar pull failed; resolve manually in $SIDECAR_DIR" >&2
    }
    ;;
  push)
    msg="${2:-}"
    [ -n "$msg" ] || { echo "usage: sidecar-sync.sh push \"<message>\"" >&2; exit 2; }
    git -C "$SIDECAR_DIR" add -A
    # Nothing staged: no empty commits, no pointless network call.
    git -C "$SIDECAR_DIR" diff --cached --quiet && exit 0
    git -C "$SIDECAR_DIR" commit --quiet -m "$msg" || exit 0
    if ! git -C "$SIDECAR_DIR" push --quiet 2>/dev/null; then
      if git -C "$SIDECAR_DIR" pull --rebase --quiet && git -C "$SIDECAR_DIR" push --quiet; then
        : # recovered
      else
        git -C "$SIDECAR_DIR" rebase --abort 2>/dev/null
        echo "WARNING: superpowers-sidecar push failed and rebase could not resolve it." >&2
        echo "         Your work IS committed locally in $SIDECAR_DIR — resolve and push manually." >&2
      fi
    fi
    ;;
  *)
    echo "usage: sidecar-sync.sh {pull|push \"<message>\"}" >&2
    exit 2
    ;;
esac
