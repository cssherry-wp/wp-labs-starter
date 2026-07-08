# wp-labs-superpowers — fork notes

This is a vendored fork of [superpowers](https://github.com/obra/superpowers), trimmed to the
plugin essentials and customized with the team docs-path convention.

## Upstream base

- Source: `obra/superpowers` (the commit pinned by `anthropics/claude-plugins-official`)
- Version: **6.1.1**
- Base commit: **`d884ae04edebef577e82ff7c4e143debd0bbec99`**
- License: MIT (see `LICENSE`)

## What diverges from upstream

1. **Docs-path convention** applied to the skill text:
   - `docs/superpowers/specs/...` → `.superpowers/01-specs/YYYY-MM-DD-HHmm-<name-of-spec>.md`
   - `docs/superpowers/plans/...` → `.superpowers/02-plans/YYYY-MM-DD-HHmm-<name-of-plan>.md`
2. **Slimmed to plugin essentials** — kept `.claude-plugin/`, `skills/`, `hooks/`, `LICENSE`,
   `README.md`; removed upstream dev/CI/test files, the upstream project's own `docs/`, and
   other-harness directories.
3. **Team workflow overlays** — spec→issue (brainstorming), plan→comment (writing-plans), and
   feature-docs (finishing-a-development-branch) are appended from `team-overlays/` after each
   rebuild.

## Why a fork (vs the overlay)

The default delivery is the lightweight `team-docs-convention` skill in the `standards` plugin.
This fork bakes the paths into the skill text. Enable **either** stock superpowers **or** this fork
— never both (they define the same skill names).

## How to refresh against a new upstream release

Run `scripts/refresh-superpowers-fork.sh` (or let the weekly
`.github/workflows/refresh-superpowers-fork.yml` do it and open a PR). The script re-copies the
plugin essentials, re-applies the path convention, re-appends the team workflow overlays, bumps the version, and updates this file.
