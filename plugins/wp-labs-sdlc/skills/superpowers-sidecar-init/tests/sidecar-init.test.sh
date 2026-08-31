#!/usr/bin/env bash
# Unit tests for sidecar-init.sh. Requires: git.
# Run: bash tests/sidecar-init.test.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/sidecar-init.sh"
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
  TMP="$(mktemp -d)"
  git init -q --bare "$TMP/sidecar-remote.git"
  git init -q --bare "$TMP/project-remote.git"
  git init -q "$TMP/project"
  git -C "$TMP/project" config user.email t@t.t
  git -C "$TMP/project" config user.name t
  git -C "$TMP/project" remote add origin "https://github.com/myorg/myrepo.git"
  echo x > "$TMP/project/README.md"
  git -C "$TMP/project" add -A && git -C "$TMP/project" commit -qm init
  export SIDECAR_DIR="$TMP/sidecar"
  export SIDECAR_URL="$TMP/sidecar-remote.git"
  export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t.t
  export GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t.t
}
teardown() { rm -rf "$TMP"; unset SIDECAR_DIR SIDECAR_URL; }

# --- key derivation from various remote URL shapes ---
setup
check "key from https remote" "$(cd "$TMP/project" && bash "$SCRIPT" key)" "myorg/myrepo"
git -C "$TMP/project" remote set-url origin "git@github.com:Other-Org/other.repo.git"
check "key from ssh remote" "$(cd "$TMP/project" && bash "$SCRIPT" key)" "Other-Org/other.repo"
git -C "$TMP/project" remote remove origin
(cd "$TMP/project" && bash "$SCRIPT" key >/dev/null 2>&1)
check "key exits 3 with no origin" "$?" "3"
teardown

# --- migrate bootstraps the clone and creates the layout ---
setup
(cd "$TMP/project" && bash "$SCRIPT" migrate) >/dev/null 2>&1
for d in 01-specs 02-plans 03-review handoff sdd; do
  check "migrate created $d" \
    "$([ -d "$TMP/sidecar/myorg/myrepo/$d" ] && echo yes || echo no)" "yes"
done
check "migrate wrote no .gitignore into subfolders" \
  "$(find "$TMP/sidecar/myorg/myrepo" -name .gitignore | wc -l | tr -d ' ')" "0"
teardown

# --- migrate moves existing local content, including 03-review and sdd ---
setup
mkdir -p "$TMP/project/.superpowers/01-specs" "$TMP/project/.superpowers/03-review" \
         "$TMP/project/.superpowers/sdd/someplan"
echo spec > "$TMP/project/.superpowers/01-specs/a.md"
echo rev  > "$TMP/project/.superpowers/03-review/r.md"
echo led  > "$TMP/project/.superpowers/sdd/someplan/ledger.md"
printf '*\n' > "$TMP/project/.superpowers/01-specs/.gitignore"
(cd "$TMP/project" && bash "$SCRIPT" migrate) >/dev/null 2>&1
check "moved a spec"   "$(cat "$TMP/sidecar/myorg/myrepo/01-specs/a.md" 2>/dev/null)" "spec"
check "moved a review" "$(cat "$TMP/sidecar/myorg/myrepo/03-review/r.md" 2>/dev/null)" "rev"
check "moved sdd state" \
  "$(cat "$TMP/sidecar/myorg/myrepo/sdd/someplan/ledger.md" 2>/dev/null)" "led"
check "dropped the old self-ignoring .gitignore" \
  "$([ -f "$TMP/sidecar/myorg/myrepo/01-specs/.gitignore" ] && echo yes || echo no)" "no"
check "local copy removed after move" \
  "$([ -f "$TMP/project/.superpowers/01-specs/a.md" ] && echo yes || echo no)" "no"
teardown

# --- collisions are reported, not overwritten ---
setup
(cd "$TMP/project" && bash "$SCRIPT" migrate) >/dev/null 2>&1   # create layout first
echo sidecar-side > "$TMP/sidecar/myorg/myrepo/01-specs/dup.md"
mkdir -p "$TMP/project/.superpowers/01-specs"
echo local-side > "$TMP/project/.superpowers/01-specs/dup.md"
echo local-only > "$TMP/project/.superpowers/01-specs/solo.md"
out="$(cd "$TMP/project" && bash "$SCRIPT" migrate 2>/dev/null)"
check "conflict reported" "$(echo "$out" | grep -c 'CONFLICT.*01-specs/dup.md')" "1"
check "sidecar copy untouched" \
  "$(cat "$TMP/sidecar/myorg/myrepo/01-specs/dup.md")" "sidecar-side"
check "local conflicting copy kept" \
  "$(cat "$TMP/project/.superpowers/01-specs/dup.md")" "local-side"
check "non-conflicting sibling still moved" \
  "$(cat "$TMP/sidecar/myorg/myrepo/01-specs/solo.md" 2>/dev/null)" "local-only"
teardown

# --- identical content on both sides is not a conflict ---
setup
(cd "$TMP/project" && bash "$SCRIPT" migrate) >/dev/null 2>&1
echo same > "$TMP/sidecar/myorg/myrepo/01-specs/same.md"
mkdir -p "$TMP/project/.superpowers/01-specs"
echo same > "$TMP/project/.superpowers/01-specs/same.md"
out="$(cd "$TMP/project" && bash "$SCRIPT" migrate 2>/dev/null)"
check "identical files are not a conflict" "$(echo "$out" | grep -c CONFLICT)" "0"
check "identical local copy cleaned up" \
  "$([ -f "$TMP/project/.superpowers/01-specs/same.md" ] && echo yes || echo no)" "no"
teardown

exit "$fail"
