# superpowers-team — fork notes

This is a vendored fork of [superpowers](https://github.com/obra/superpowers), trimmed to the
plugin essentials and customized with the team docs-path convention.

## Upstream base

- Source: `obra/superpowers` (shipped via `anthropics/claude-plugins-official`)
- Version: **6.0.2**
- Base commit: **`b62616fc12f6a007c6fd5118146821d748da0d33`**
- License: MIT (see `LICENSE`)

## What diverges from upstream

1. **Docs-path convention** applied to the skill text:
   - `docs/superpowers/specs/...` → `docs/01-specs/YYYY-MM-DD-HHmm-<name-of-spec>.md`
   - `docs/superpowers/plans/...` → `docs/02-plans/YYYY-MM-DD-HHmm-<name-of-plan>.md`
   - Files touched: `skills/brainstorming/SKILL.md`,
     `skills/brainstorming/spec-document-reviewer-prompt.md`,
     `skills/writing-plans/SKILL.md`, `skills/requesting-code-review/SKILL.md`,
     `skills/subagent-driven-development/SKILL.md`.
2. **Slimmed to plugin essentials** — kept `.claude-plugin/`, `skills/`, `hooks/`, `LICENSE`,
   `README.md`. Removed upstream dev/CI/test files, the upstream project's own `docs/`, and
   other-harness directories (codex/cursor/gemini/kimi/opencode/pi), none of which the Claude
   Code plugin needs at runtime.

Nothing else in the skill logic is changed.

## Why a fork (vs the overlay)

The default delivery is the lightweight `team-docs-convention` skill in the `standards` plugin,
which steers stock superpowers via instruction precedence. This fork bakes the paths directly
into the skill text for teams that prefer not to rely on instruction precedence. Enable **either**
stock superpowers **or** this fork — never both (they define the same skill names).

## How to refresh against a new upstream release

This is automated. The weekly workflow `.github/workflows/refresh-superpowers-fork.yml`
checks upstream and opens a PR when the version changed.

To do it manually (or test), run:

```bash
scripts/refresh-superpowers-fork.sh           # rebuild if upstream is newer
scripts/refresh-superpowers-fork.sh --check   # report only, no changes
```

The script re-copies the plugin essentials, re-applies the path convention
(`docs/superpowers/specs` → `docs/01-specs`, `docs/superpowers/plans` → `docs/02-plans`,
plus the `HHmm` filename pattern), bumps `version` in `.claude-plugin/plugin.json`, and
rewrites the "Upstream base" section above. Review the diff before committing.
