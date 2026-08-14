# Repository instructions

## Plugin version bumps

Any change to a plugin under `plugins/` MUST increment that plugin's `version` in its
`.claude-plugin/plugin.json`. Follow [semver](https://semver.org):

- **major** (`X.0.0`) — breaking or large changes.
- **minor** (`0.X.0`) — new backward-compatible features.
- **patch** (`0.0.X`) — small fixes, docs, and tweaks.

Bump in the same PR as the change. A plugin change without a version bump is incomplete.

A `pre-commit` git hook (`.githooks/pre-commit`) blocks the commit when a changed plugin's
`version` isn't greater than `origin/main`'s, and when `wp-labs-sdlc`'s `SDLC_SOURCE_VERSION`
(see below) doesn't match its `plugin.json`. It only sees whatever `origin/main` last resolved
to locally — `git fetch` first if unsure. One-time setup per clone, since `.githooks` isn't
git's default hooks path:

```
git config core.hooksPath .githooks
```

The same rule runs in CI (`.github/workflows/ci.yml`, "Plugin version bump check" job) via the
shared `.githooks/check-plugin-versions` script, comparing the PR's head commit against its
base branch — a backstop for anyone who hasn't set `core.hooksPath` or who commits with
`--no-verify`.

### wp-labs-sdlc: sync statusline.sh version

Whenever `plugins/wp-labs-sdlc/.claude-plugin/plugin.json`'s `version` changes, also update
`SDLC_SOURCE_VERSION` in
`plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/statusline.sh` to match, then
copy the file to the live location:

```
cp plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/statusline.sh \
   ~/.claude/statusline.sh
```

The statusline footer shows this hardcoded version next to the installed plugin's actual
cache version, flagging when they drift — that check is only useful if the hardcoded value
tracks `plugin.json`.

## session-dashboard.html deploy

After any edit to `plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/session-dashboard.html`,
copy it to the live location:

```
cp plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/session-dashboard.html \
   ~/ClaudeAnalytics/session-dashboard.html
```

Do this before committing so the deployed file stays in sync with the template.

## wp-labs-superpowers fork

See [`plugins/wp-labs-superpowers/FORK_MODIFICATIONS.md`](plugins/wp-labs-superpowers/FORK_MODIFICATIONS.md) for what the fork changes and how to update it.

## Commits reference an issue

If the commit addresses a tracker issue, add a reference at the end of the commit body:

- **GitHub**: trailer on its own line — `Closes #123` when this commit resolves the issue, `Refs #123` when it relates but doesn't close it
- **Jira**: prefix the subject line — `PROJ-123: <summary>` — and add `Refs PROJ-123` as a trailer when a commit shares multiple issues
- Omit entirely when no issue applies; do not create an issue just to have one to reference

## Worktree-safe repo root

Inside a git worktree, `git rev-parse --show-toplevel` returns the **worktree path**, not the main repo root. Always use:

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
```

This works correctly from both the main working tree and any worktree.

## Global config note

`~/.claude/CLAUDE.md` (the user-level config) is outside this repository. Changes to it cannot be committed here. Edit it directly and track it separately (e.g. in a dotfiles repo). Do not attempt to stage or commit it from within claude-starter.
