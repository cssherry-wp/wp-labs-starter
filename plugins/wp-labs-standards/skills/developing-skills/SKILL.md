---
name: developing-skills
description: Use when creating or editing skills inside a plugin in this repo
user-invocable: false
---

# Developing Skills

## Background

Read `wp-labs-superpowers:writing-skills` first — it covers skill TDD, frontmatter spec,
description writing, SDO, and the full creation checklist. This guide covers
plugin-specific mechanics only.

## Visibility

| Location | Frontmatter | Result |
|---|---|---|
| `skills/<name>/SKILL.md` | _(none)_ or `user-invocable: true` | Listed, invocable by user |
| `skills/<name>/SKILL.md` | `user-invocable: false` | Hidden from user; Claude auto-loads it |
| `skills/<name>/references/*.md` | _(no frontmatter)_ | Internal reference; never auto-loaded |

Non-skill reference material (heavy API docs, guides like this one) belongs in
`references/` inside a skill directory, or in a top-level `guides/` directory.

## Testing After Editing

```
edit SKILL.md → sync-cache → invoke skill in Claude → verify behavior
```

No Claude restart needed. `sync-cache` (in `scripts/`) syncs the active cache entry;
without it, your edits are invisible to the running session.

## Naming

- Directory name = kebab-case = `name:` field in frontmatter
- Letters, numbers, hyphens only — no parentheses or special characters
- Plugin prefix added automatically: `wp-labs-standards:my-skill`

## Scripts in Skills

Prefer scripts over prose for deterministic behavior. Every script under `scripts/`
should have a paired `test-<script>` file. See `scripts/sync-cache` and
`scripts/test-sync-cache` for the pattern.

Use a hook + setup mode when you want to skip the LLM entirely for a command.
See `developing-plugins` skill for the hook+setup pattern.
