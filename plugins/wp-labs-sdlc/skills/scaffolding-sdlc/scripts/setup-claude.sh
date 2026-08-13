#!/usr/bin/env bash
# Bootstrap or sync the global Claude Code environment from wp-labs-sdlc templates.
# Run on a fresh machine before opening any project in Claude Code, or with
# --sync to non-interactively apply any drifted files.
#
# Config dir resolution: --claude-dir > $CLAUDE_CONFIG_DIR > ~/.claude
#
# Usage: bash path/to/setup-claude.sh [--claude-dir DIR] [--sync]
set -euo pipefail

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq" >&2
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMPL="$SKILL_DIR/templates/claude"

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SYNC=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-dir) CLAUDE_DIR="$2"; shift 2 ;;
    --sync) SYNC=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

ask() {
  local prompt="$1"
  if $SYNC; then return 0; fi
  local yn
  read -r -p "$prompt [y/N] " yn
  [[ "$yn" =~ ^[Yy] ]]
}

# --- settings.json ---
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  # Merge objects recursively; concatenate hooks.Stop arrays so existing hooks are preserved.
  merged=$(jq -s '.[0] as $a | .[1] as $b | ($a * $b) | .hooks.Stop = (($a.hooks.Stop // []) + ($b.hooks.Stop // []))' "$CLAUDE_DIR/settings.json" "$TMPL/settings.json")
  if diff <(cat "$CLAUDE_DIR/settings.json") <(echo "$merged") > /dev/null 2>&1; then
    echo "settings.json: already up to date"
  else
    if ! $SYNC; then
      echo "settings.json diff (existing -> merged):"
      diff <(cat "$CLAUDE_DIR/settings.json") <(echo "$merged") || true
    fi
    if ask "Apply merge?"; then
      echo "$merged" > "$CLAUDE_DIR/settings.json"
      echo "settings.json: merged"
    else
      echo "settings.json: skipped"
    fi
  fi
else
  cp "$TMPL/settings.json" "$CLAUDE_DIR/settings.json"
  echo "settings.json: created"
fi

# --- CLAUDE.md ---
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
  if diff -q "$CLAUDE_DIR/CLAUDE.md" "$TMPL/CLAUDE.md" > /dev/null 2>&1; then
    echo "CLAUDE.md: already up to date"
  else
    if ! $SYNC; then
      echo "CLAUDE.md diff (existing -> template):"
      diff "$CLAUDE_DIR/CLAUDE.md" "$TMPL/CLAUDE.md" || true
    fi
    if ask "Overwrite CLAUDE.md?"; then
      cp "$TMPL/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
      echo "CLAUDE.md: updated"
    else
      echo "CLAUDE.md: skipped"
    fi
  fi
else
  cp "$TMPL/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
  echo "CLAUDE.md: created"
fi

# --- statusline.sh ---
src="$TMPL/statusline.sh"
dst="$CLAUDE_DIR/statusline.sh"
if [ -f "$src" ]; then
  if [ -f "$dst" ] && diff -q "$src" "$dst" > /dev/null 2>&1; then
    echo "statusline.sh: already up to date"
  else
    cp "$src" "$dst"
    chmod +x "$dst"
    echo "statusline.sh: installed"
  fi
fi

# --- rules/* ---
if [ -d "$TMPL/rules" ]; then
  mkdir -p "$CLAUDE_DIR/rules"
  for src in "$TMPL/rules/"*; do
    [ -e "$src" ] || continue
    dst="$CLAUDE_DIR/rules/$(basename "$src")"
    if [ -f "$dst" ] && diff -q "$src" "$dst" > /dev/null 2>&1; then
      echo "rules/$(basename "$src"): already up to date"
    else
      cp "$src" "$dst"
      echo "rules/$(basename "$src"): installed"
    fi
  done
fi

# --- session-dashboard.html ---
src="$TMPL/session-dashboard.html"
ANALYTICS_DIR="${CLAUDE_ANALYTICS_DIR:-$HOME/ClaudeAnalytics}"
dst="$ANALYTICS_DIR/session-dashboard.html"
if [ -f "$src" ]; then
  mkdir -p "$ANALYTICS_DIR"
  if [ -f "$dst" ] && diff -q "$src" "$dst" > /dev/null 2>&1; then
    echo "session-dashboard.html: already up to date"
  else
    cp "$src" "$dst"
    echo "session-dashboard.html: installed to $ANALYTICS_DIR/"
  fi
fi

echo ""
if $SYNC; then
  echo "Sync complete. Run /reload-plugins in Claude Code to pick up any settings changes."
else
  echo "Done. Restart Claude Code to pick up the new settings."
  echo "Plugins listed in settings.json will auto-install on first launch."
fi
