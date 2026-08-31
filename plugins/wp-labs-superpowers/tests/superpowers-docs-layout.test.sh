#!/usr/bin/env bash
# Guards the .superpowers/ layout that the superpowers sidecar depends on.
#
# Deliberately lives OUTSIDE skills/: build_fork_tree in
# scripts/refresh-superpowers-fork.sh does `rm -rf $dest/skills` on every
# rebuild, so a test placed in there would be deleted and, worse, reported as
# hand-edit drift.
#
# Two things are checked:
#   1. sdd-workspace resolves a plan-scoped directory and writes no .gitignore.
#   2. No skill still instructs anyone to drop a self-ignoring .gitignore into
#      .superpowers/ or its subfolders. A `*` marker anywhere under there makes
#      git ignore the tree inside the sidecar clone, so the content is silently
#      never committed or pushed — the failure is invisible until you look for
#      a spec on another machine and it isn't there.
#
# Run: bash plugins/wp-labs-superpowers/tests/superpowers-docs-layout.test.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PLUGIN="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$PLUGIN/../.." && pwd)"
WORKSPACE="$PLUGIN/skills/subagent-driven-development/scripts/sdd-workspace"
OVERLAY="$PLUGIN/team-overlays/files/skills/subagent-driven-development/scripts/sdd-workspace"
fail=0

check() {
  local name="$1" got="$2" want="$3"
  if [ "$got" = "$want" ]; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"; echo "  want: $want"; echo "  got:  $got"; fail=1
  fi
}

# --- 1. sdd-workspace ---------------------------------------------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git init -q "$TMP/repo"
mkdir -p "$TMP/repo/.superpowers/02-plans"
echo "# plan" > "$TMP/repo/.superpowers/02-plans/2026-01-01-0900-a-plan.md"

out="$(cd "$TMP/repo" && bash "$WORKSPACE" .superpowers/02-plans/2026-01-01-0900-a-plan.md 2>&1)"
check "sdd-workspace prints a plan-scoped directory" \
  "$(basename "$out")" "2026-01-01-0900-a-plan"
check "sdd-workspace created the directory" \
  "$([ -d "$out" ] && echo yes || echo no)" "yes"
check "sdd-workspace wrote no .gitignore anywhere under .superpowers" \
  "$(find "$TMP/repo/.superpowers" -name .gitignore | wc -l | tr -d ' ')" "0"

# A second plan must not share the first plan's workspace: a stale ledger read
# as current progress makes a controller skip whole task sequences.
echo "# plan b" > "$TMP/repo/.superpowers/02-plans/2026-01-02-0900-b-plan.md"
out2="$(cd "$TMP/repo" && bash "$WORKSPACE" .superpowers/02-plans/2026-01-02-0900-b-plan.md 2>&1)"
check "a second plan gets its own workspace" \
  "$([ "$out" != "$out2" ] && echo yes || echo no)" "yes"

check "sdd-workspace rejects a missing plan file" \
  "$(cd "$TMP/repo" && bash "$WORKSPACE" nope.md >/dev/null 2>&1; echo $?)" "2"

# Every team-overlays/files/ entry is the source of truth the fork rebuild copies
# back over the live tree; if the two drift, a rebuild silently reverts the
# committed file to whatever the overlay holds.
check "overlay copy of sdd-workspace matches the live one" \
  "$(cmp -s "$WORKSPACE" "$OVERLAY" && echo same || echo differ)" "same"

while IFS= read -r overlaid; do
  rel="${overlaid#"$PLUGIN/team-overlays/files/"}"
  check "whole-file overlay $rel matches the live file" \
    "$(cmp -s "$overlaid" "$PLUGIN/$rel" && echo same || echo differ)" "same"
done < <(find "$PLUGIN/team-overlays/files" -type f 2>/dev/null | sort)

# --- 2. no self-ignoring .gitignore instructions remain -----------------------
# Match a .gitignore write whose path is under .superpowers, on one line.
offenders="$(grep -rIl --include='*.md' --include='sdd-workspace' \
  -E "(printf|echo)[^|]*'\*'[^|]*>[^|]*\.superpowers|\.superpowers/[^ ]*/\.gitignore" \
  "$REPO/plugins" "$REPO/docs" "$REPO/CLAUDE.md" 2>/dev/null \
  | grep -v '/tests/' | sort)"
check "no skill or doc instructs a self-ignoring .gitignore under .superpowers" \
  "$offenders" ""

# The convention doc should state the rule positively, so the next author knows
# the omission is deliberate rather than an oversight.
# shellcheck disable=SC2016  # backticks are literal markdown in the search string
check "team-docs-convention states the do-not-create rule" \
  "$(grep -c 'Do not create a `.gitignore` inside' \
     "$REPO/plugins/wp-labs-standards/skills/team-docs-convention/SKILL.md")" "1"

for d in 01-specs 02-plans 03-review; do
  check "team-docs-convention names $d" \
    "$(grep -c "$d" "$REPO/plugins/wp-labs-standards/skills/team-docs-convention/SKILL.md" | \
       awk '{print ($1 > 0) ? "yes" : "no"}')" "yes"
done

# --- 2b. the spec is git-ignored, not committed --------------------------------
# Upstream brainstorming tells the user to commit the design document; the team
# convention is that .superpowers/ is git-ignored and the tracker issue is the
# spec's durable record. build_fork_tree rewrites those sentences in place, so
# the contradiction reappearing here means a rewrite stopped matching upstream's
# wording and silently did nothing.
BRAINSTORM="$PLUGIN/skills/brainstorming/SKILL.md"
check "brainstorming says the spec is a git-ignored working copy" \
  "$(grep -c 'git-ignored working copy' "$BRAINSTORM")" "2"
check "brainstorming says not to commit the spec" \
  "$(grep -c 'Do NOT commit the spec' "$BRAINSTORM")" "1"
check "brainstorming no longer tells anyone to commit the spec" \
  "$(grep -cE 'and commit$|^- Commit the design document to git$|Spec written and committed' \
     "$BRAINSTORM")" "0"

# --- 3. every overlay fragment is actually applied to its skill ---------------
# The refresh script only appends overlays when it rebuilds from a new upstream
# release, so a fragment added or edited on its own sits inert until then — the
# SKILL.md Claude loads would not carry the change. Both failure directions have
# happened: a new fragment never applied, and an edited fragment applied only in
# part. The committed overlay region must equal the fragment byte for byte.
for frag in "$PLUGIN"/team-overlays/*.md; do
  [ -e "$frag" ] || continue
  skill="$(basename "$frag" .md)"
  target="$PLUGIN/skills/$skill/SKILL.md"
  if [ ! -f "$target" ]; then
    check "overlay $skill targets an existing skill" "missing: $target" ""
    continue
  fi
  begin="$(grep -n 'wp-labs team overlay: BEGIN' "$target" | head -1 | cut -d: -f1)"
  if [ -z "$begin" ]; then
    check "overlay $skill is applied to its SKILL.md" "not applied" "applied"
    continue
  fi
  check "overlay $skill matches its SKILL.md region" \
    "$(sed -n "${begin},\$p" "$target" | diff -q - "$frag" >/dev/null && echo same || echo differ)" \
    "same"
done

exit "$fail"
