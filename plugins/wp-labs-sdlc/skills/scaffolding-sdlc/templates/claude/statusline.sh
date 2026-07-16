#!/usr/bin/env bash
# Claude Code status bar: ponytail mode | active model | config directory

pt=$(bash "$(ls -d "$HOME"/.claude/plugins/cache/ponytail/ponytail/*/hooks/ponytail-statusline.sh 2>/dev/null | sort -V | tail -1)" 2>/dev/null || true)
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
model=$(jq -r '.model // ""' "$cfg/settings.json" 2>/dev/null || true)

echo "${pt:+$pt | }${model:+$model | }${cfg/$HOME/~}"
