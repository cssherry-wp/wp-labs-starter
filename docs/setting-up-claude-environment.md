# Setting Up the Claude Environment

**Goal:** Configure the global `~/.claude/` environment — plugins, settings, coding rules, and output style — so Claude Code behaves consistently across all projects on a machine.

## When to use this

- Fresh machine or new Claude Code install
- Onboarding a new team member
- Syncing your global Claude config to the team standard after the plugin is updated

For per-repo setup (CI, workflows, pre-commit), use the `scaffolding-sdlc` skill without any flags.

## Option 1: Via the skill (Claude running)

Invoke the skill with the `--setup-claude` flag in any Claude Code session:

```
/scaffolding-sdlc --setup-claude
```

Claude will walk through each component interactively — showing diffs and asking before applying anything.

## Option 2: Standalone script (bootstrap without Claude)

Run this directly from the `claude-starter` repo when Claude Code isn't configured yet:

```bash
git clone https://github.com/cssherry-wp/wp-labs-starter.git
cd wp-labs-starter
bash plugins/wp-labs-sdlc/skills/scaffolding-sdlc/scripts/setup-claude.sh
```

The script is interactive: for each file it shows a diff against what's already in `~/.claude/` and prompts `[y/N]` before applying. Identical files are skipped silently.

Optional flag:

```bash
bash scripts/setup-claude.sh --claude-dir /path/to/custom/.claude
```

## What gets configured

| File | What it does |
|------|-------------|
| `~/.claude/settings.json` | Registers marketplaces (wp-labs-starter, ponytail, playwright-skill), enables all recommended plugins, sets the Ponytail status line, Stop hook for uncommitted changes, `defaultMode: plan`, `alwaysThinkingEnabled: true` |
| `~/.claude/CLAUDE.md` | Git commit policy, ambiguity handling, prose output style rules |
| `~/.claude/rules/coding-guidelines.md` | Always-on coding conventions (KISS, function length, immutability, security) |
| `~/.claude/rules/python.md` | Python-specific rules loaded for `*.py` files |
| `~/.claude/rules/js-ts.md` | JS/TS/React rules loaded for `*.js,*.ts,*.tsx,*.jsx` files |
| `~/.claude/rules/css.md` | CSS/Sass rules loaded for `*.css,*.scss,*.sass` files |
| `~/.claude/rules/sql.md` | SQL rules loaded for `*.sql` files |
| `~/.claude/rules/context7.md` | Instructs Claude to fetch live library docs via `npx ctx7@latest` |

## Plugin auto-install

After `settings.json` is in place, restart Claude Code. It reads `enabledPlugins` and auto-installs any plugin not yet cached, pulling from the registered marketplaces. No manual `claude plugins install` needed.

Prerequisites: `jq` (`brew install jq`) for the settings merge step.

## Keeping it up to date

The templates live in `plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/`. When the plugin version bumps, re-run `--setup-claude` or the script — it merges rather than overwrites, so local additions are preserved.
