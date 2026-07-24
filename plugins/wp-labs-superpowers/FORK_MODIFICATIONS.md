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

## Sync to a new upstream release

Run `scripts/refresh-superpowers-fork.sh` (or let the weekly CI workflow open a PR). It rebuilds `skills/` and `hooks/` from the upstream snapshot pinned by `anthropics/claude-plugins-official`, re-applies path rewrites, re-appends overlays, copies extra files, and bumps the version.
