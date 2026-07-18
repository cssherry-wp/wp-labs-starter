#!/usr/bin/env bash
# Claude Code status bar: git context | ponytail mode | active model | config directory

pt=$(bash "$(ls -d "$HOME"/.claude/plugins/cache/ponytail/ponytail/*/hooks/ponytail-statusline.sh 2>/dev/null | sort -V | tail -1)" 2>/dev/null || true)
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
model=$(jq -r '.model // ""' "$cfg/settings.json" 2>/dev/null || true)

git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
folder=$(basename "${git_root:-$PWD}")
branch=$(git branch --show-current 2>/dev/null || true)
git_ctx="${folder}${branch:+ [$branch]}"

echo "${git_ctx:+$git_ctx | }${pt:+$pt | }${model:+$model | }${cfg/$HOME/~}"
