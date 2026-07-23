#!/usr/bin/env bash
# Bootstrap the global Claude Code environment from the wp-labs-sdlc templates.
# Run this on a fresh machine before opening any project in Claude Code.
# Claude Code will auto-install plugins listed in settings.json on next launch.
#
# Usage: bash path/to/setup-claude.sh [--claude-dir DIR]
set -euo pipefail

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq" >&2
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMPL="$SKILL_DIR/templates/claude"

CLAUDE_DIR="$HOME/.claude"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-dir) CLAUDE_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

ask() {
  local prompt="$1"
  local yn
  read -r -p "$prompt [y/N] " yn
  [[ "$yn" =~ ^[Yy] ]]
}

# --- settings.json ---
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  # Merge objects recursively; concatenate hooks.Stop arrays so existing hooks are preserved.
  merged=$(jq -s '.[0] * .[1] | .hooks.Stop = ((.[0].hooks.Stop // []) + (.[1].hooks.Stop // []))' "$CLAUDE_DIR/settings.json" "$TMPL/settings.json")
  if diff <(cat "$CLAUDE_DIR/settings.json") <(echo "$merged") > /dev/null 2>&1; then
    echo "settings.json: already up to date"
  else
    echo "settings.json diff (existing -> merged):"
    diff <(cat "$CLAUDE_DIR/settings.json") <(echo "$merged") || true
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
    echo "CLAUDE.md diff (existing -> template):"
    diff "$CLAUDE_DIR/CLAUDE.md" "$TMPL/CLAUDE.md" || true
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

echo ""
echo "Done. Restart Claude Code to pick up the new settings."
echo "Plugins listed in settings.json will auto-install on first launch."
