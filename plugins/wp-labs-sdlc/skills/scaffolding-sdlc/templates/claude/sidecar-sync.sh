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
#   sidecar-sync.sh sweep               # push with a session-end message the
#                                       # script builds itself (Stop hook)
set -uo pipefail

SIDECAR_DIR="${SIDECAR_DIR:-$HOME/.superpowers-sidecar}"

# The .superpowers symlink lives in the MAIN working tree. A git worktree has no
# copy of it, so resolving $PWD alone would make every worktree session a silent
# no-op — and worktrees are where a lot of work actually happens. Resolve the
# main working tree the same way CLAUDE.md prescribes.
project_root() {
  local gcd root
  gcd="$(git rev-parse --git-common-dir 2>/dev/null)" || { echo "$PWD"; return; }
  root="$(cd "$gcd/.." 2>/dev/null && pwd -P)" || { echo "$PWD"; return; }
  echo "$root"
}

ROOT="$(project_root)"
LINK="$ROOT/.superpowers"

# Not adopted (or no sidecar clone yet) -> silent no-op.
[ -L "$LINK" ] || exit 0
[ -d "$SIDECAR_DIR/.git" ] || exit 0

# <org>/<repo> for this project, derived from where the symlink points. Used to
# prefix commit messages so one sidecar repo's history stays readable.
project_key() {
  local target
  target="$(cd -P "$LINK" 2>/dev/null && pwd -P)" || { echo unknown; return; }
  echo "$(basename "$(dirname "$target")")/$(basename "$target")"
}

# Refuse to publish credentials. The sidecar remote is shared, and specs and
# plans routinely quote real tokens and connection strings while being drafted;
# `git add -A` would push them without this gate. Warn loudly, commit nothing,
# and leave the working tree untouched so the author can redact and retry.
# Set SIDECAR_ALLOW_SECRETS=1 to override a false positive.
secret_scan() { # -> 0 if clean, 1 if something looks like a credential
  [ "${SIDECAR_ALLOW_SECRETS:-}" = "1" ] && return 0
  # Only the newly staged lines are scanned. Scanning all tracked content would
  # mean one already-committed false positive wedges every future push.
  local pat hits
  pat="AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
  pat="$pat|gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}"
  pat="$pat|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}"
  pat="$pat|(api[_-]?key|secret|password|passwd|token|client[_-]?secret)[[:space:]]*[:=][[:space:]]*[\"']?[A-Za-z0-9/+_=-]{16,}"
  hits="$(git -C "$SIDECAR_DIR" diff --cached -U0 \
    | awk '/^\+\+\+ /{f=substr($0,7)} /^\+/ && !/^\+\+\+/ {print f": "substr($0,2)}' \
    | grep -iE "$pat" \
    | head -20)"
  [ -z "$hits" ] && return 0
  echo "WARNING: superpowers-sidecar push BLOCKED — the staged changes look like they contain secrets:" >&2
  printf '         %s\n' "$hits" >&2
  echo "         Nothing was committed or pushed. Redact the values in $SIDECAR_DIR, then re-run." >&2
  echo "         If this is a false positive: SIDECAR_ALLOW_SECRETS=1 <your command>" >&2
  return 1
}

do_push() {
  local msg="$1"
  git -C "$SIDECAR_DIR" add -A
  # Nothing staged: no empty commits, no pointless network call.
  git -C "$SIDECAR_DIR" diff --cached --quiet && exit 0
  if ! secret_scan; then
    git -C "$SIDECAR_DIR" reset --quiet
    exit 1
  fi
  git -C "$SIDECAR_DIR" commit --quiet -m "$msg" || exit 0
  if ! git -C "$SIDECAR_DIR" push --quiet; then
    if git -C "$SIDECAR_DIR" pull --rebase --quiet && git -C "$SIDECAR_DIR" push --quiet; then
      : # recovered
    else
      git -C "$SIDECAR_DIR" rebase --abort 2>/dev/null
      echo "WARNING: superpowers-sidecar push failed and rebase could not resolve it." >&2
      echo "         Your work IS committed locally in $SIDECAR_DIR — resolve and push manually." >&2
    fi
  fi
}

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
    do_push "$msg"
    ;;
  sweep)
    # The Stop hook's whole job. Keeping the message here rather than inline in
    # settings.json means the key derivation exists once, in the one place that
    # already knows how to find the project.
    do_push "$(project_key): session-end sweep ($(date '+%Y-%m-%d %H:%M'))"
    ;;
  *)
    echo "usage: sidecar-sync.sh {pull|push \"<message>\"|sweep}" >&2
    exit 2
    ;;
esac
