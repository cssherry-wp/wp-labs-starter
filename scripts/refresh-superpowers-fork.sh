#!/usr/bin/env bash
# Refresh the vendored wp-labs-superpowers fork from the superpowers snapshot that
# anthropics/claude-plugins-official currently pins (a specific, vetted
# obra/superpowers commit) — i.e. track Anthropic's curated release, not
# upstream HEAD.
#
# Detects a new upstream release by comparing the upstream plugin.json `version`
# against our fork's base version (the part before the `-team.N` suffix). If they
# differ, it rebuilds plugins/wp-labs-superpowers from upstream and re-applies the
# team docs-path convention. It does NOT commit — the CI workflow (or you) commits
# and opens the PR.
#
# Usage:
#   scripts/refresh-superpowers-fork.sh           # rebuild fork if upstream is newer
#   scripts/refresh-superpowers-fork.sh --check   # report only, make no changes
#
# Outputs (also written to $GITHUB_OUTPUT when set): changed, version, sha
set -euo pipefail

MARKETPLACE_REPO="https://github.com/anthropics/claude-plugins-official.git"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FORK_DIR="$ROOT/plugins/wp-labs-superpowers"
MODE="${1:-refresh}"

emit() { [ -n "${GITHUB_OUTPUT:-}" ] && echo "$1" >>"$GITHUB_OUTPUT" || true; }
ver() { node -e 'console.log(require(process.argv[1]).version)' "$1"; }

current_version=$(ver "$FORK_DIR/.claude-plugin/plugin.json")
current_base="${current_version%%-team*}"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Resolve the superpowers source the official marketplace currently blesses: its
# manifest pins obra/superpowers to a specific, vetted commit. Building from that
# commit tracks Anthropic's curated snapshot rather than upstream HEAD.
git clone --quiet --depth 1 "$MARKETPLACE_REPO" "$TMP/mp"
read -r src_url src_sha <<<"$(node -e '
  const m = require(process.argv[1]);
  const p = (m.plugins || []).find((x) => x.name === "superpowers");
  if (!p || !p.source || !p.source.url) {
    console.error("superpowers source not found in official marketplace manifest");
    process.exit(1);
  }
  process.stdout.write(p.source.url + " " + (p.source.sha || ""));
' "$TMP/mp/.claude-plugin/marketplace.json")"

# Fetch just the pinned commit (falls back to default HEAD if the manifest pins
# by branch rather than sha).
src="$TMP/up"
mkdir -p "$src"
git -C "$src" init -q
git -C "$src" fetch --quiet --depth 1 "$src_url" "${src_sha:-HEAD}"
git -C "$src" checkout --quiet FETCH_HEAD
upstream_version=$(ver "$src/.claude-plugin/plugin.json")
upstream_sha=$(git -C "$src" rev-parse HEAD)

if [ "$upstream_version" = "$current_base" ]; then
  echo "Up to date: fork base $current_base == upstream $upstream_version"
  emit "changed=false"
  exit 0
fi

echo "New upstream version detected: $upstream_version (current fork base: $current_base)"
emit "changed=true"
emit "version=$upstream_version"
emit "sha=$upstream_sha"

# NOTE: --check does not exit here. It falls through the drift check below and
# exits after it, so `--check` actually reports hand-edits that the rebuild
# would discard — reporting drift is the main thing a dry run is asked for.
# Only the rebuild itself is skipped.

# Rebuild $2 (skills/ + hooks/ + LICENSE/README) from upstream checkout $1,
# apply the docs-path convention, then re-append team-overlays/ fragments.
# Used both for the real rebuild and for reconstructing what the fork
# *should* look like from its recorded base, to detect drift (see below).
build_fork_tree() {
  local src="$1" dest="$2"
  rm -rf "$dest/skills" "$dest/hooks" "$dest/LICENSE" "$dest/README.md"
  cp -R "$src/skills" "$dest/skills"
  [ -d "$src/hooks" ] && cp -R "$src/hooks" "$dest/hooks"
  [ -f "$src/LICENSE" ] && cp "$src/LICENSE" "$dest/LICENSE"
  [ -f "$src/README.md" ] && cp "$src/README.md" "$dest/README.md"
  # Drop other-harness hook variants and any cruft; never vendor a nested marketplace.json
  rm -f "$dest/hooks/hooks-codex.json" "$dest/hooks/hooks-cursor.json"
  rm -rf "$dest/hooks/session-start-codex"
  rm -f "$dest/.claude-plugin/marketplace.json"
  find "$dest" -name '.DS_Store' -delete

  # --- Apply the team docs-path convention to the skill text ------------------
  while IFS= read -r f; do
    sed -i.bak -e 's#docs/superpowers/specs#.superpowers/01-specs#g' \
               -e 's#docs/superpowers/plans#.superpowers/02-plans#g' "$f"
    rm -f "$f.bak"
  done < <(grep -rl 'docs/superpowers/\(specs\|plans\)' "$dest/skills" 2>/dev/null || true)

  # Best-effort HHmm filename patterns (skip silently if upstream changed the wording).
  # NOTE: the loop above has already rewritten the docs/superpowers/{specs,plans}
  # prefix to .superpowers/{01-specs,02-plans}, so these patterns must match the
  # already-rewritten prefix — not the original upstream one.
  sed -i.bak 's#.superpowers/01-specs/YYYY-MM-DD-<topic>-design\.md#.superpowers/01-specs/YYYY-MM-DD-HHmm-<name-of-spec>.md#g' \
    "$dest/skills/brainstorming/SKILL.md" 2>/dev/null && rm -f "$dest/skills/brainstorming/SKILL.md.bak" || true
  sed -i.bak 's#.superpowers/02-plans/YYYY-MM-DD-<feature-name>\.md#.superpowers/02-plans/YYYY-MM-DD-HHmm-<name-of-plan>.md#g' \
    "$dest/skills/writing-plans/SKILL.md" 2>/dev/null && rm -f "$dest/skills/writing-plans/SKILL.md.bak" || true

  # --- "commit the spec" -> the team's git-ignored-spec convention ------------
  # Upstream tells the user to commit the design document. Under the team
  # convention .superpowers/ is git-ignored working space and the tracker issue
  # is the spec's durable record, so these three sentences have to be replaced
  # in place. Appending an overlay cannot contradict prose that already says
  # the opposite, and pinning the whole file as a team-overlays/files/ entry
  # would discard every upstream improvement to this skill — a rewrite here is
  # the same mechanism the docs-path substitutions above use.
  # Each is exact-match, idempotent, and best-effort: if upstream rewords the
  # sentence the substitution simply does not fire, and the drift check is what
  # tells us to come back and update the pattern.
  bs="$dest/skills/brainstorming/SKILL.md"
  if [ -f "$bs" ]; then
    sed -i.bak \
      -e 's#<name-of-spec>\.md` and commit#<name-of-spec>.md` (git-ignored working copy; not committed)#' \
      -e 's#^- Commit the design document to git$#- Do NOT commit the spec — `.superpowers/` is git-ignored working space in the host repo; the GitHub tracking issue (see the "Team workflow" section at the end of this skill) is its durable record there. Instead, push it to the sidecar (same section), passing the same summary you give the user as the commit message.#' \
      -e 's#^> "Spec written and committed to `<path>`\.#> "Spec written to `<path>` (git-ignored working copy).#' \
      "$bs" 2>/dev/null && rm -f "$bs.bak" || true
  fi

  # --- worktree creation -> cd immediately, point at the sidecar-symlink step -
  # Upstream has no notion of the sidecar, and never calls out that a native
  # tool may not actually leave you positioned in the new worktree — so there's
  # no existing sentence to rewrite here (unlike the "commit the spec" block
  # above). These substitutions each append onto an existing anchor line
  # instead, one per path that lands you in a newly created worktree. Each is
  # exact-match, idempotent, and best-effort, same as the docs-path rules above.
  uwt="$dest/skills/using-git-worktrees/SKILL.md"
  if [ -f "$uwt" ]; then
    sed -i.bak \
      -e 's#Skip to Step 2 (Project Setup)\. Do NOT create another worktree\.#Skip to Step 2 (Project Setup). Do NOT create another worktree. First run the sidecar-symlink step in the "Team workflow" section at the end of this skill.#' \
      -e 's#If you do, use it and skip to Step 2\.#If you do, use it. **Immediately `cd` into the new worktree'"'"'s path** — a native tool creates the directory but does not always leave your active directory there; confirm with `pwd` if unsure, and never continue work from the original directory. Then run the sidecar-symlink step in the "Team workflow" section at the end of this skill, and skip to Step 2.#' \
      -e 's@^cd "\$path"$@cd "$path"   # do this immediately — never continue work from the original directory\
\
# Give this worktree its own sidecar symlink if the project is adopted — see\
# the "Team workflow" section at the end of this skill.@' \
      -e 's#| "The workspace is fresh — baseline tests can wait" \| A dirty baseline makes every later failure ambiguous\. Run the tests now; proceeding past failures is your human partner'"'"'s call\. \|#&\n| "The native tool surely left me in the new worktree" | Confirm with `pwd`. Working from the original directory while believing you'"'"'re isolated is worse than no isolation — every edit lands in the wrong place. |#' \
      "$uwt" 2>/dev/null && rm -f "$uwt.bak" || true
  fi

  # --- worktree isolation -> ask, never assume --------------------------------
  # Upstream tells the controller to just create/verify an isolated workspace.
  # The team wants the human asked each time instead of it being assumed —
  # using-git-worktrees' own Step 0 already asks, but only when the caller
  # hasn't already "declared a preference"; upstream's directive phrasing reads
  # as exactly that declared preference, which is what suppressed the ask.
  # Same exact-match/idempotent/best-effort mechanism as the blocks above.
  ep="$dest/skills/executing-plans/SKILL.md"
  if [ -f "$ep" ]; then
    sed -i.bak \
      -e 's#^1\. Ensure an isolated workspace: use superpowers:using-git-worktrees to create one or verify the existing one$#1. Ask whether to execute in an isolated git worktree or in the current directory — do not assume isolation is wanted. If they want isolation, use superpowers:using-git-worktrees to create one or verify the existing one#' \
      "$ep" 2>/dev/null && rm -f "$ep.bak" || true
  fi
  sdd="$dest/skills/subagent-driven-development/SKILL.md"
  if [ -f "$sdd" ]; then
    sed -i.bak \
      -e 's#^Ensure the work happens in an isolated workspace: use$#Ask whether to execute in an isolated git worktree or in the current directory — do not assume#' \
      -e 's#^superpowers:using-git-worktrees to create one or verify the existing one\.$#isolation is wanted. If they want isolation, use superpowers:using-git-worktrees to create one or\nverify the existing one.#' \
      "$sdd" 2>/dev/null && rm -f "$sdd.bak" || true
  fi

  # --- Re-apply team workflow overlays (survive the upstream rebuild) --------
  # Overlays live only in the real fork, not in reconstructions of it.
  local overlay_dir="$FORK_DIR/team-overlays"
  if [ -d "$overlay_dir" ]; then
    for frag in "$overlay_dir"/*.md; do
      [ -e "$frag" ] || continue
      skill_name=$(basename "$frag" .md)
      target="$dest/skills/$skill_name/SKILL.md"
      [ -f "$target" ] || continue
      if ! grep -q 'wp-labs team overlay: BEGIN' "$target"; then
        printf '\n' >>"$target"
        cat "$frag" >>"$target"
      fi
    done

    # Whole-file overlays: everything that is not SKILL.md prose — scripts,
    # hook payloads — where the team version replaces upstream's outright
    # rather than being appended to it. team-overlays/files/ mirrors the fork
    # layout, so team-overlays/files/skills/foo/scripts/bar overwrites
    # skills/foo/scripts/bar. Copied last so it wins over the upstream copy.
    # -p keeps the executable bit, which scripts here depend on.
    if [ -d "$overlay_dir/files" ]; then
      cp -Rp "$overlay_dir/files"/. "$dest"/
    fi
  fi
}

# --- Detect fork edits that bypass the overlay mechanism ----------------------
# Any hand-edit made directly to skills/ or hooks/ (a SKILL.md tweak, a script
# fix) instead of a team-overlays/ fragment is invisible to the rebuild below
# and gets silently discarded. Reconstruct what the fork should look like from
# its recorded base commit + rewrites + current overlays, and diff that
# against what's actually committed — any mismatch is an undocumented edit
# about to be lost.
base_sha=$(sed -n 's/.*Base commit: \*\*`\([0-9a-f]*\)`\*\*.*/\1/p' "$FORK_DIR/FORK.md" 2>/dev/null)
if [ -z "$base_sha" ]; then
  echo "WARNING: could not read a base commit from FORK.md — skipping the drift check; hand-edits outside team-overlays/ will not be detected." >&2
fi
if [ -n "$base_sha" ]; then
  old_src="$TMP/old"
  mkdir -p "$old_src"
  git -C "$old_src" init -q
  if git -C "$old_src" fetch --quiet --depth 1 "$src_url" "$base_sha" 2>/dev/null; then
    git -C "$old_src" checkout --quiet FETCH_HEAD
    expected="$TMP/expected"
    mkdir -p "$expected/.claude-plugin"
    build_fork_tree "$old_src" "$expected"
    drift=$( { diff -rq "$expected/skills" "$FORK_DIR/skills" 2>/dev/null
               [ -d "$expected/hooks" ] && diff -rq "$expected/hooks" "$FORK_DIR/hooks" 2>/dev/null
               true; } )
    if [ -n "$drift" ]; then
      echo "ERROR: fork files were hand-edited outside team-overlays/ — the rebuild would discard them:" >&2
      echo "$drift" >&2
      echo "Fix: move SKILL.md prose into a team-overlays/<skill>.md fragment, and any other file" >&2
      echo "into team-overlays/files/<same-path> (see FORK_MODIFICATIONS.md), then re-run." >&2
      echo "To rebuild anyway and accept the loss, set FORCE=1." >&2
      [ "${FORCE:-}" = "1" ] || exit 1
    fi
    [ "$MODE" = "--check" ] && echo "No hand-edit drift: the rebuild would preserve every fork file."
  else
    echo "WARNING: could not fetch base commit $base_sha from $src_url — skipping the drift check; hand-edits outside team-overlays/ will not be detected." >&2
  fi
fi

if [ "$MODE" = "--check" ]; then
  exit 0
fi

# --- Rebuild the fork from upstream, keeping only plugin essentials -----------
build_fork_tree "$src" "$FORK_DIR"

# --- Rewrite our plugin manifest and FORK.md ---------------------------------
new_version="${upstream_version}-team.1"
node - "$FORK_DIR/.claude-plugin/plugin.json" "$new_version" <<'NODE'
const fs = require("fs");
const [, , file, version] = process.argv;
const manifest = {
  name: "wp-labs-superpowers",
  description:
    "Team fork of superpowers (TDD, debugging, brainstorming, plans) with the team docs-path convention baked in. Enable instead of stock superpowers — never both.",
  version,
  author: { name: "Sherry Zhou", email: "szhou@wp-labs.ai" },
  homepage: "https://github.com/cssherry-wp/wp-labs-starter",
  repository: "https://github.com/cssherry-wp/wp-labs-starter",
  license: "MIT",
  keywords: ["skills", "tdd", "debugging", "collaboration", "best-practices", "workflows", "fork"],
};
fs.writeFileSync(file, JSON.stringify(manifest, null, 2) + "\n");
NODE

cat >"$FORK_DIR/FORK.md" <<EOF
# wp-labs-superpowers — fork notes

This is a vendored fork of [superpowers](https://github.com/obra/superpowers), trimmed to the
plugin essentials and customized with the team docs-path convention.

## Upstream base

- Source: \`obra/superpowers\` (the commit pinned by \`anthropics/claude-plugins-official\`)
- Version: **${upstream_version}**
- Base commit: **\`${upstream_sha}\`**
- License: MIT (see \`LICENSE\`)

## What diverges from upstream

1. **Docs-path convention** applied to the skill text:
   - \`docs/superpowers/specs/...\` → \`.superpowers/01-specs/YYYY-MM-DD-HHmm-<name-of-spec>.md\`
   - \`docs/superpowers/plans/...\` → \`.superpowers/02-plans/YYYY-MM-DD-HHmm-<name-of-plan>.md\`
2. **Slimmed to plugin essentials** — kept \`.claude-plugin/\`, \`skills/\`, \`hooks/\`, \`LICENSE\`,
   \`README.md\`; removed upstream dev/CI/test files, the upstream project's own \`docs/\`, and
   other-harness directories.
3. **Team workflow overlays** — spec→issue (brainstorming), plan→comment (writing-plans),
   feature-docs (finishing-a-development-branch), and diff-coverage + test conventions
   (test-driven-development) are appended from \`team-overlays/\` after each rebuild.

## Why a fork (vs the overlay)

The default delivery is the lightweight \`team-docs-convention\` skill in the \`standards\` plugin.
This fork bakes the paths into the skill text. Enable **either** stock superpowers **or** this fork
— never both (they define the same skill names).

## How to refresh against a new upstream release

Run \`scripts/refresh-superpowers-fork.sh\` (or let the weekly
\`.github/workflows/refresh-superpowers-fork.yml\` do it and open a PR). The script re-copies the
plugin essentials, re-applies the path convention, re-appends the team workflow overlays, bumps the version, and updates this file.
EOF

echo "Rebuilt wp-labs-superpowers at version $new_version (upstream sha $upstream_sha)"
