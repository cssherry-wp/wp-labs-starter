---
name: developing-plugins
description: Use when creating, editing, or testing a Claude Code plugin in this repo
user-invocable: false
---

# Developing Plugins

## Plugin Structure

```
plugins/<name>/
  .claude-plugin/
    plugin.json          # name, version, description, author (required)
  hooks/
    hooks.json           # hook event registrations (uses ${CLAUDE_PLUGIN_ROOT})
    <hook-script>        # executable scripts run by hooks
  skills/
    <skill-name>/
      SKILL.md           # user-visible unless user-invocable: false
  scripts/               # utility scripts; each has a paired test-* script
  guides/                # non-skill reference docs (not auto-discovered)
```

## Version Bumping

Every change to any file under `plugins/<name>/` MUST bump the version in
`.claude-plugin/plugin.json` (semver: patch for fixes/docs, minor for features,
major for breaking). No exceptions — a change without a bump is incomplete.

## Cache Mechanics

Claude Code caches installed plugin versions at:
`~/.claude/plugins/cache/<org>/<plugin>/<version>/`

The **active version** is selected at runtime:
- Has `.in_use` marker
- Has no `.orphaned_at` marker
- Highest semver among qualifying entries

Editing the source does nothing until the active cache entry is updated.

## Cache Refresh Workflow

**After every edit, always run:**
```bash
plugins/wp-labs-standards/scripts/sync-cache
```

This syncs source → active cache using `shutil.copytree` (excludes `.claude-plugin`).
No Claude restart needed for skill/hook content changes. Restart required only when
registering a brand-new hook event type.

The script auto-detects the plugin root (walks up looking for `.claude-plugin/plugin.json`)
and the active cache entry. Use `--dry-run` to preview without writing.

**Test the script first:**
```bash
plugins/wp-labs-standards/scripts/test-sync-cache
```

## Hook + Setup Pattern (Skip LLM Entirely)

Use when a command should bypass the LLM for speed or determinism (e.g. `/queue` capture).

**Two-part pattern:**

1. **Plugin hook** (`hooks/hooks.json`): fires automatically via `${CLAUDE_PLUGIN_ROOT}`.
   Returns `{"decision":"block","reason":"<output>"}` to short-circuit the LLM, or
   `{"hookSpecificOutput":{"additionalContext":"..."}}` to inject context and let LLM handle it.

2. **User-installed hook** (`skills/<skill>/hook` + setup mode): the skill's setup mode
   copies the hook script to `~/.claude/<skill>/hook` and registers it in
   `~/.claude/settings.json` as a persistent `UserPromptSubmit` hook. The hook reads
   the prompt from stdin JSON (`jq -r '.prompt'`) and intercepts specific commands.

Key decisions:
- **Block entirely** → `{"decision":"block","reason":"..."}`
- **Inject context, let LLM decide** → `{"hookSpecificOutput":{"additionalContext":"..."}}`
- **Pass through** → `exit 0`

See `plugins/wp-labs-sdlc/skills/queue/hook` for the canonical implementation.

## Workflow Summary

```
edit source → bump version → sync-cache → test in Claude Code → commit
```

Never commit without syncing and verifying the behavior in the active session.
Skipping sync is the most common reason "my change isn't working."
