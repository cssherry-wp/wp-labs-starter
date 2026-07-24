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

Every commit MUST reference the GitHub issue it addresses via a trailer — `Closes #123` when
the commit completes the issue, otherwise `Refs #123`. If no issue exists for the change, create
one first (`gh issue create`), then reference it.
