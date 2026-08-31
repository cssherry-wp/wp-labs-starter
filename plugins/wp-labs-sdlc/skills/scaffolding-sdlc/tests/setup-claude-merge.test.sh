#!/usr/bin/env bash
# Regression test for setup-claude.sh's settings.json hook merge.
#
# Two ways this merge has broken before, both silent:
#   1. jq's `*` replaces arrays, so a user's own hooks vanished entirely.
#   2. Dedup compared whole hook *group* objects, so upgrading from a template
#      that shipped a smaller group left the old copy behind and ran its hooks
#      twice.
# Both are invisible until someone reads their merged settings.json, hence this
# check runs the real merge expression out of the real script.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script="$here/../scripts/setup-claude.sh"
template="$here/../templates/claude/settings.json"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

fails=0
ok()   { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { # description, expected, actual
  if [ "$2" = "$3" ]; then
    ok "$1"
  else
    bad "$1"; echo "  expected: $2"; echo "  actual:   $3"
  fi
}

# Pull the jq program straight out of setup-claude.sh so the test cannot drift
# from the implementation it is guarding.
sed -n "/^  merged=\$(jq -s '/,/\"\$TMPL\/settings.json\")\$/p" "$script" \
  | sed -e "1s/^  merged=\$(jq -s '//" -e "\$d" \
  | sed -e "s/' *\\\\\$//" -e "s/'\$//" > "$tmp/merge.jq"
[ -s "$tmp/merge.jq" ] || { echo "FAIL: could not extract the merge program from $script"; exit 1; }

merge() { jq -s -f "$tmp/merge.jq" "$1" "$template"; }
commands() { jq -c "[.hooks.$1[]?.hooks[]?.command]"; }

# --- 1. A user's own hook survives the merge -----------------------------------
jq -n '{hooks:{Stop:[{hooks:[{type:"command",command:"mine"}]}]}}' > "$tmp/own.json"
check "user's own Stop hook is preserved" \
  "true" \
  "$(merge "$tmp/own.json" | commands Stop | grep -q '"mine"' && echo true || echo false)"

# --- 2. Merging the template into itself is idempotent -------------------------
merge "$template" > "$tmp/twice.json"
check "re-running the merge does not duplicate Stop hooks" \
  "$(commands Stop < "$template")" \
  "$(commands Stop < "$tmp/twice.json")"
check "re-running the merge does not duplicate SessionStart hooks" \
  "$(commands SessionStart < "$template")" \
  "$(commands SessionStart < "$tmp/twice.json")"

# --- 3. Upgrading from a template that shipped a smaller group ------------------
# Drop the last hook of each shipped group to stand in for an older template,
# then merge the current one over it: the shared hooks must appear exactly once.
jq '.hooks |= with_entries(.value |= map(.hooks |= (if length > 1 then .[0:-1] else . end)))' \
  "$template" > "$tmp/older.json"
merge "$tmp/older.json" > "$tmp/upgraded.json"
for evt in Stop SessionStart; do
  shipped=$(commands "$evt" < "$template" | jq -r '.[]')
  while IFS= read -r cmd; do
    [ -n "$cmd" ] || continue
    n=$(commands "$evt" < "$tmp/upgraded.json" | jq --arg c "$cmd" '[.[] | select(. == $c)] | length')
    check "$evt hook appears exactly once after upgrade" "1" "$n"
  done <<< "$shipped"
done

[ "$fails" = "0" ] || exit 1
