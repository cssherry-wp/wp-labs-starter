#!/usr/bin/env bash
# Unit tests for sidecar-init-all-worktrees.sh. Requires: git.
# Run: bash tests/sidecar-init-all-worktrees.test.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/sidecar-init-all-worktrees.sh"
fail=0

check() {
  local name="$1" got="$2" want="$3"
  if [ "$got" = "$want" ]; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"; echo "  want: $want"; echo "  got:  $got"; fail=1
  fi
}

setup() {
  TMP="$(cd "$(mktemp -d)" && pwd -P)"
  git init -q "$TMP/project"
  git -C "$TMP/project" config user.email t@t.t
  git -C "$TMP/project" config user.name t
  git -C "$TMP/project" commit -q --allow-empty -m init
}
teardown() { rm -rf "$TMP"; }

setup
out="$(cd "$TMP/project" && bash "$SCRIPT")"
check "lists just the main repo before any worktree exists" "$out" "$TMP/project"

git -C "$TMP/project" worktree add -q -b wt1 "$TMP/project-wt1" >/dev/null 2>&1
out="$(cd "$TMP/project" && bash "$SCRIPT")"
check "includes main repo" "$(echo "$out" | grep -c "^$TMP/project\$")" "1"
check "includes linked worktree" "$(echo "$out" | grep -c "^$TMP/project-wt1\$")" "1"

out2="$(cd "$TMP/project-wt1" && bash "$SCRIPT")"
check "same list from inside the worktree" "$out2" "$out"
teardown

TMP="$(cd "$(mktemp -d)" && pwd -P)"
(cd "$TMP" && bash "$SCRIPT" >/dev/null 2>&1)
check "exits 1 outside a git repository" "$?" "1"
rm -rf "$TMP"

exit "$fail"
