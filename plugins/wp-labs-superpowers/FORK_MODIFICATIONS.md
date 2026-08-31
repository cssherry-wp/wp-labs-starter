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
3. Append the same fragment to the committed `skills/<skill-name>/SKILL.md` now. The refresh script only applies overlays when it rebuilds, so a fragment added on its own sits inert until the next upstream release — the skill Claude actually loads would not carry your change.

## Add or edit a whole-file overlay (scripts, hooks, anything not `SKILL.md`)

Appending prose does not work for a script. For those, `team-overlays/files/` mirrors the fork's own
layout, and every file in it is copied over the rebuilt tree at the end of the refresh:

```
team-overlays/files/skills/subagent-driven-development/scripts/sdd-workspace
  -> overwrites  skills/subagent-driven-development/scripts/sdd-workspace
```

The copy runs last, so the team version always wins over upstream's. Keep the two copies identical
(`plugins/wp-labs-superpowers/tests/superpowers-docs-layout.test.sh` asserts this): edit the
`team-overlays/files/` copy, then copy it into `skills/`, or the next refresh reverts your committed
change to whatever the overlay holds.

Use this only for a file the team genuinely owns end to end. A whole-file overlay pins that file at
the version you wrote, so upstream improvements to it are silently discarded on every refresh —
prefer a `team-overlays/<skill>.md` fragment whenever the change can be expressed as appended prose.

## Change how the fork is built

Structural changes — path rewrites, file pruning, version logic — live in [`scripts/refresh-superpowers-fork.sh`](https://github.com/cssherry-wp/wp-labs-starter/blob/main/scripts/refresh-superpowers-fork.sh). Edit that script, then run it to verify the rebuild produces the expected result.

## Never hand-edit `skills/` or `hooks/` directly

Any edit made straight to a file under `skills/` or `hooks/` — a tweak to a `SKILL.md`, a fix to a
script like `skills/brainstorming/scripts/helper.js` — is invisible to the refresh script and gets
silently wiped the next time it rebuilds from upstream, because the rebuild replaces those
directories wholesale. Only `team-overlays/` content and the rewrites baked into the script survive
a refresh.

The refresh script now guards against this: before rebuilding, it reconstructs what the fork should
look like from its recorded base commit and diffs that against what's actually committed. A mismatch
means something was hand-edited outside the overlay system, and the script aborts with the list of
affected files instead of quietly discarding them. Move the change into a `team-overlays/<skill>.md`
fragment for `SKILL.md` prose, or into `team-overlays/files/<same-path>` for any other file (see the
two sections above).

**To verify the guard actually fires** (worth a quick check after touching the guard itself, since a
silent no-op here is worse than no guard at all): the drift check is skipped only when the script
exits "Up to date", i.e. whenever `plugin.json`'s version already matches upstream — true right
after every refresh. When upstream *is* ahead, `--check` runs the drift check and reports it without
rebuilding, so that is the cheap way to ask "would a refresh discard anything?". To force the check
while up to date, work from a throwaway copy of the repo:

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
