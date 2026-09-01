#!/usr/bin/env bash
# Print every place a local .superpowers/ could exist for this project: the
# main repo root plus each linked git worktree, one per line.
#
# sidecar-init.sh itself only ever acts on $PWD — it stays a single-root
# script. This one just enumerates roots; the skill loops sidecar-init.sh's
# migrate/finalize over them with `cd "$root" && ...`.
set -uo pipefail

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "not inside a git repository" >&2; exit 1; }

git worktree list --porcelain | awk '/^worktree /{print substr($0, 10)}'
