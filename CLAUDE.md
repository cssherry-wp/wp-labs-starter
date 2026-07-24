# Repository instructions

## Plugin version bumps

Any change to a plugin under `plugins/` MUST increment that plugin's `version` in its
`.claude-plugin/plugin.json`. Follow [semver](https://semver.org):

- **major** (`X.0.0`) — breaking or large changes.
- **minor** (`0.X.0`) — new backward-compatible features.
- **patch** (`0.0.X`) — small fixes, docs, and tweaks.

Bump in the same PR as the change. A plugin change without a version bump is incomplete.

## wp-labs-superpowers fork

See [`plugins/wp-labs-superpowers/FORK_MODIFICATIONS.md`](plugins/wp-labs-superpowers/FORK_MODIFICATIONS.md) for what the fork changes and how to update it.

## Commits reference an issue

If the commit addresses a tracker issue, add a reference at the end of the commit body:

- **GitHub**: trailer on its own line — `Closes #123` when this commit resolves the issue, `Refs #123` when it relates but doesn't close it
- **Jira**: prefix the subject line — `PROJ-123: <summary>` — and add `Refs PROJ-123` as a trailer when a commit shares multiple issues
- Omit entirely when no issue applies; do not create an issue just to have one to reference

<!-- session-summarize: Worktree-safe repo root: use git -C git-common-dir/.. instead of git rev-parse - -->
## Worktree-safe repo root

Inside a git worktree, `git rev-parse --show-toplevel` returns the **worktree path**, not the main repo root. Always use:

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
```

This works correctly from both the main working tree and any worktree.

## Global config note

`~/.claude/CLAUDE.md` (the user-level config) is outside this repository. Changes to it cannot be committed here. Edit it directly and track it separately (e.g. in a dotfiles repo). Do not attempt to stage or commit it from within claude-starter.
