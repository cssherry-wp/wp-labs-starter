---
name: setup-claude
description: >-
  Configure the global Claude Code environment (settings, plugins, CLAUDE.md,
  rules, statusline) from wp-labs-sdlc templates. Uses $CLAUDE_CONFIG_DIR if
  set, otherwise ~/.claude. No args: initial setup on a fresh machine. --sync:
  non-interactively apply any files that have drifted from the latest plugin
  templates.
user-invocable: true
argument-hint: "[--sync]"
disable-model-invocation: true
allowed-tools: Bash
---

# /setup-claude

Two modes:

- **No args**: Initial setup on a fresh machine or new Claude Code install.
  Runs the script interactively — shows diffs and prompts before writing each file.

- **`--sync`**: Sync drifted files against the latest plugin templates without
  prompting. Use after a plugin version bump to apply updates.

## Running

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/scaffolding-sdlc/scripts/setup-claude.sh" "$@"
```

Pass `--sync` through to the script when the user invokes with `--sync`.

After the script exits, tell the user to run `/reload-plugins` (or restart
Claude Code) if any settings files were changed.
