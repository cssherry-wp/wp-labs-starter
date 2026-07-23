#!/usr/bin/env bash
set -euo pipefail
# Claude Code status bar: git context | ponytail mode | active model | config directory

pt=$(bash "$(ls -d "$HOME"/.claude/plugins/cache/ponytail/ponytail/*/hooks/ponytail-statusline.sh 2>/dev/null | sort | tail -1)" 2>/dev/null || true)
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
# Precedence: env var → project settings → user settings
model="${ANTHROPIC_MODEL:-}"
if [[ -z "$model" && -n "$git_root" ]]; then
  model=$(jq -r '.model // ""' "$git_root/.claude/settings.json" 2>/dev/null || true)
fi
if [[ -z "$model" ]]; then
  model=$(jq -r '.model // ""' "$cfg/settings.json" 2>/dev/null || true)
fi

folder=$(basename "${git_root:-$PWD}")
branch=$(git branch --show-current 2>/dev/null || true)
git_ctx="${folder}${branch:+ [$branch]}"

echo "${git_ctx:+$git_ctx | }${pt:+$pt | }${model:+$model | }${cfg/$HOME/~}"
