# How to modify the wp-labs-superpowers fork

See `FORK.md` for what the current fork differs from upstream. This file explains how to add or change team modifications so they survive future upstream refreshes.

## Add or edit a skill overlay

Overlays are appended to a skill's `SKILL.md` after each upstream refresh. To add one:

1. Create `team-overlays/<skill-name>.md` wrapped in the required markers:
   ```
   <!-- wp-labs team overlay: BEGIN -->
   ...your additions...
   <!-- wp-labs team overlay: END -->
   ```
2. The refresh script (`scripts/refresh-superpowers-fork.sh`) appends it automatically. It checks for the `BEGIN` marker so it won't double-append.

## Change how the fork is built

Structural changes — path rewrites, file pruning, version logic — live in [`scripts/refresh-superpowers-fork.sh`](https://github.com/cssherry-wp/wp-labs-starter/blob/main/scripts/refresh-superpowers-fork.sh). Edit that script, then run it to verify the rebuild produces the expected result.

## Never hand-edit `skills/` or `hooks/` directly

Any edit made straight to a file under `skills/` or `hooks/` — a tweak to a `SKILL.md`, a fix to a
script like `skills/brainstorming/scripts/helper.js` — is invisible to the refresh script and gets
silently wiped the next time it rebuilds from upstream, because the rebuild replaces those
directories wholesale. Only `team-overlays/*.md` fragments and the rewrites baked into the script
survive a refresh.

The refresh script now guards against this: before rebuilding, it reconstructs what the fork should
look like from its recorded base commit and diffs that against what's actually committed. A mismatch
means something was hand-edited outside the overlay system, and the script aborts with the list of
affected files instead of quietly discarding them. Move the change into a `team-overlays/<skill>.md`
fragment (for `SKILL.md` content) — non-`SKILL.md` files (scripts, etc.) currently have no overlay
mechanism, so re-apply those by hand after each refresh, or extend the script if they recur.

**To verify the guard actually fires** (worth a quick check after touching the guard itself, since a
silent no-op here is worse than no guard at all): the drift check only runs on the rebuild path,
which the script skips with "Up to date" whenever `plugin.json`'s version already matches upstream
— true right after every refresh. To force it, work from a throwaway copy of the repo:

```bash
cp -R . /tmp/fork-drift-test && cd /tmp/fork-drift-test
# Fake a pending refresh so the script takes the rebuild path instead of exiting "Up to date":
node -e '
  const fs = require("fs");
  const p = "plugins/wp-labs-superpowers/.claude-plugin/plugin.json";
  const m = JSON.parse(fs.readFileSync(p));
  m.version = "6.0.0-team.1";
  fs.writeFileSync(p, JSON.stringify(m, null, 2) + "\n");
'
echo '<!-- test -->' >> plugins/wp-labs-superpowers/skills/writing-plans/SKILL.md
bash scripts/refresh-superpowers-fork.sh; echo "exit: $?"
```

Expect `ERROR: fork files were hand-edited outside team-overlays/ ...` naming
`writing-plans/SKILL.md`, and a non-zero exit — confirmed working as of the 6.2.0 refresh. If the
run instead prints a `WARNING: ... skipping the drift check` (or nothing), the guard didn't run —
see the two `WARNING` cases in the script (missing base commit in `FORK.md`, or the base-commit
fetch failing) before assuming the fork is drift-free.

## Sync to a new upstream release

Run `scripts/refresh-superpowers-fork.sh` (or let the weekly CI workflow open a PR). It rebuilds `skills/` and `hooks/` from the upstream snapshot pinned by `anthropics/claude-plugins-official`, re-applies path rewrites, re-appends overlays, copies extra files, and bumps the version.
