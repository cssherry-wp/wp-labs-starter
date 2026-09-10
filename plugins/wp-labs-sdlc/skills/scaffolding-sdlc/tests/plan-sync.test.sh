#!/usr/bin/env bash
# Unit tests for plan-sync.sh. Builds a fake $HOME, transcript and adopted
# project in a temp dir. Requires: git. Run: bash tests/plan-sync.test.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../templates/claude/plan-sync.sh"
fail=0

check() {
  local name="$1" got="$2" want="$3"
  if [ "$got" = "$want" ]; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"; echo "  want: $want"; echo "  got:  $got"; fail=1
  fi
}

# Fake $HOME with a plans dir, plus a git project adopted via a .superpowers
# symlink (the guard the script requires).
setup() {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/home/.claude/plans" "$TMP/sidecar/02-plans" "$TMP/outside"
  git init -q "$TMP/project"
  ln -s "$TMP/sidecar" "$TMP/project/.superpowers"
}
teardown() { rm -rf "$TMP"; }

# Run the hook from the project with the fake HOME and a transcript of $1.
run() {
  printf '%s' "$1" > "$TMP/transcript.jsonl"
  printf '{"transcript_path": "%s"}' "$TMP/transcript.jsonl" \
    | (cd "$TMP/project" && HOME="$TMP/home" bash "$SCRIPT" 2>&1)
}
plan_count() { find "$TMP/sidecar/02-plans" -name '*.md' | wc -l | tr -d ' '; }

# --- a plan under $HOME/.claude/plans is copied once, idempotently ---
setup
echo plan > "$TMP/home/.claude/plans/mine.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}" > /dev/null
check "copied the session's plan" "$(plan_count)" "1"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}" > /dev/null
check "rerun is idempotent" "$(plan_count)" "1"
teardown

# --- planFilePath with whitespace around the colon still matches ---
setup
echo plan > "$TMP/home/.claude/plans/esc.md"
out="$(run "{\"input\":{\"planFilePath\"   :   \"$TMP/home/.claude/plans/esc.md\"}}")"
check "whitespace-around-colon field is copied" "$(plan_count)" "1"
check "whitespace case reports success" "$(echo "$out" | grep -c '^OK: copied 1 plan')" "1"
teardown

# --- the planFilePath JSON record still matches embedded in a longer line ---
setup
echo plan > "$TMP/home/.claude/plans/embed.md"
out="$(run "prefix noise {\"type\":\"tool_use\",\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/embed.md\",\"plan\":\"...\"}} trailing noise")"
check "planFilePath embedded in a longer line is copied" "$(plan_count)" "1"
check "embedded case reports success" "$(echo "$out" | grep -c '^OK: copied 1 plan')" "1"
teardown

# --- CR-001 regression: a path in prose only (no planFilePath field) is NOT copied ---
setup
echo plan > "$TMP/home/.claude/plans/prose.md"
out="$(run "see \`$TMP/home/.claude/plans/prose.md\` for details")"
check "prose-only path is not copied" "$(plan_count)" "0"
check "prose-only path prints nothing" "$out" ""
teardown

# --- a path outside $HOME/.claude/plans is never copied ---
setup
mkdir -p "$TMP/outside/.claude/plans"
echo secret > "$TMP/outside/.claude/plans/evil.md"
out="$(run "{\"input\":{\"planFilePath\":\"$TMP/outside/.claude/plans/evil.md\"}}")"
check "path outside HOME is not copied" "$(plan_count)" "0"
check "path outside HOME prints nothing" "$out" ""
teardown

# --- a symlinked plan is not dereferenced ---
setup
echo id_rsa > "$TMP/secret"
ln -s "$TMP/secret" "$TMP/home/.claude/plans/link.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/link.md\"}}" > /dev/null
check "symlinked plan is not copied" "$(plan_count)" "0"
teardown

# --- an unadopted project creates nothing and exits 0 ---
setup
rm "$TMP/project/.superpowers"
echo plan > "$TMP/home/.claude/plans/mine.md"
out="$(run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}"; echo "rc=$?")"
check "unadopted project is a silent no-op" "$out" "rc=0"
check "unadopted project created no .superpowers" \
  "$([ -e "$TMP/project/.superpowers" ] && echo yes || echo no)" "no"
teardown

# --- no OK: output when nothing was copied ---
setup
echo plan > "$TMP/home/.claude/plans/mine.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}" > /dev/null
out="$(run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}")"
check "silent when already synced" "$out" ""
out="$(run "no plan paths here at all"; echo "rc=$?")"
check "silent when no plan path in transcript" "$out" "rc=0"
teardown

# --- CR-014: a plan revised later in the session is copied as a new dated file ---
setup
echo "plan v1" > "$TMP/home/.claude/plans/mine.md"
touch -t 202601010000 "$TMP/home/.claude/plans/mine.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}" > /dev/null
check "first version copied" "$(plan_count)" "1"
echo "plan v2 - revised" > "$TMP/home/.claude/plans/mine.md"
touch -t 202601020000 "$TMP/home/.claude/plans/mine.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}" > /dev/null
check "revised plan copied as a second dated file" "$(plan_count)" "2"
teardown

# --- idempotency: unchanged plan on rerun is not re-copied, prints nothing ---
setup
echo "plan v1" > "$TMP/home/.claude/plans/mine.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}" > /dev/null
out="$(run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/mine.md\"}}")"
check "unchanged plan is not re-copied" "$(plan_count)" "1"
check "unchanged plan prints nothing" "$out" ""
teardown

# --- CR-012: slug collision with an existing dated file for a different slug ---
setup
mkdir -p "$TMP/sidecar/02-plans"
echo "unrelated plan" > "$TMP/sidecar/02-plans/2026-01-01-0000-plan-sync.md"
echo "actual plan" > "$TMP/home/.claude/plans/sync.md"
run "{\"input\":{\"planFilePath\":\"$TMP/home/.claude/plans/sync.md\"}}" > /dev/null
check "slug collision does not block a different plan" "$(plan_count)" "2"
teardown

exit "$fail"
