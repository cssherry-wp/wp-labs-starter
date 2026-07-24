# wp-labs-superpowers — team modifications

This plugin is a fork of [`superpowers`](https://github.com/obra/superpowers). See `FORK.md` (auto-generated on each refresh) for the upstream base version and commit.

## What the fork changes

All structural changes (path convention rewrites, file pruning) are applied by `scripts/refresh-superpowers-fork.sh` on each upstream sync.

Team workflow additions are appended to skill files from `team-overlays/`:

- `brainstorming.md` — spec→issue workflow
- `writing-plans.md` — plan→comment workflow
- `finishing-a-development-branch.md` — feature-docs step

The `test-driven-development` skill has additional team content baked directly into the skill file (not via an overlay): diff coverage check, test conventions, mocking policy, and testing anti-patterns. These survive upstream refreshes only if manually re-applied after a sync.

## How to update the fork

To change **how the fork is built** (path rewrites, file pruning, version logic): edit [`scripts/refresh-superpowers-fork.sh`](https://github.com/cssherry-wp/wp-labs-starter/blob/main/scripts/refresh-superpowers-fork.sh).

To add or change **team workflow content**: edit files in `plugins/wp-labs-superpowers/team-overlays/`. These are re-appended automatically on every upstream refresh.

To sync to a **new upstream release**: run `scripts/refresh-superpowers-fork.sh` (or let the weekly CI workflow do it and open a PR).
