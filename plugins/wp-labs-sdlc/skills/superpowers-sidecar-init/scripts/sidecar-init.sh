#!/usr/bin/env bash
# Adopt the current project into the global superpowers sidecar repo.
#
# Split into phases because conflict resolution needs a human in between:
#   key       -> print <org>/<repo> for this project
#   migrate   -> bootstrap clone, create layout, move non-colliding files,
#                print "CONFLICT<TAB><path>" for anything that would be
#                overwritten (nothing is ever overwritten here)
#   finalize  -> replace .superpowers with the symlink, ignore it, sync
#
# The skill drives the phases and handles the conversation about conflicts;
# this script only does mechanical work so it stays testable.
set -uo pipefail

SIDECAR_DIR="${SIDECAR_DIR:-$HOME/.superpowers-sidecar}"
SUBDIRS="01-specs 02-plans 03-review handoff sdd"

die() { echo "$1" >&2; exit "${2:-1}"; }

project_key() {
  local url
  url="$(git remote get-url origin 2>/dev/null)" || die "no 'origin' remote — sidecar adoption needs one" 3
  [ -n "$url" ] || die "no 'origin' remote — sidecar adoption needs one" 3
  # git@host:org/repo.git | https://host/org/repo.git | https://host/org/repo
  url="${url%.git}"
  url="${url##*:}"          # strip scheme/host for ssh form
  url="${url#//}"
  # For https URLs the host is still attached; keep only the last two segments.
  echo "$url" | awk -F/ '{ if (NF>=2) print $(NF-1)"/"$NF; else print $NF }'
}

ensure_clone() {
  [ -d "$SIDECAR_DIR/.git" ] && return 0
  local url="${SIDECAR_URL:-$(git config --global superpowers.sidecarUrl 2>/dev/null)}"
  [ -n "$url" ] || die "no sidecar remote configured. Set it with:
  git config --global superpowers.sidecarUrl <url>" 4
  git clone --quiet "$url" "$SIDECAR_DIR" \
    || die "could not clone sidecar remote: $url" 4
}

case "${1:-}" in
  key)
    project_key
    ;;

  migrate)
    key="$(project_key)" || exit $?
    ensure_clone
    dest="$SIDECAR_DIR/$key"
    for d in $SUBDIRS; do mkdir -p "$dest/$d"; done

    src="$PWD/.superpowers"
    # Nothing local to migrate (or already a symlink): layout creation was the job.
    { [ -d "$src" ] && [ ! -L "$src" ]; } || exit 0

    # Walk every real file. Directories are recreated, never moved wholesale,
    # so a collision is decided per file rather than per folder.
    find "$src" -type f -print | while IFS= read -r file; do
      rel="${file#"$src"/}"
      case "$rel" in
        .gitignore|*/.gitignore)
          # The old self-ignoring markers exist only to hide content from the
          # *project* repo. Inside the sidecar this content is meant to be
          # tracked, so these are dropped rather than carried over.
          rm -f "$file"
          continue
          ;;
      esac
      target="$dest/$rel"
      if [ -e "$target" ]; then
        if cmp -s "$file" "$target"; then
          rm -f "$file"          # same content: nothing to decide
        else
          printf 'CONFLICT\t%s\n' "$rel"
        fi
        continue
      fi
      mkdir -p "$(dirname "$target")"
      mv "$file" "$target"
    done

    # Clean up directories the moves emptied; anything left holds a conflict.
    find "$src" -type d -empty -delete 2>/dev/null
    exit 0
    ;;

  *)
    die "usage: sidecar-init.sh {key|migrate|finalize}" 2
    ;;
esac
