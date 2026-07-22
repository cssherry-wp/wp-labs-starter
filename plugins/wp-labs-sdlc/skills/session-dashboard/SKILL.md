---
name: session-dashboard
description: >-
  Open the Claude session history dashboard in the browser. Shows sessions,
  costs, queue items, tool usage, and PR links across projects. Use when the
  user asks what they've done this session, wants to review costs, or wants
  to explore session history.
user-invocable: true
allowed-tools: Bash
---

# /session-dashboard — open the session dashboard

Open `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/session-dashboard.html` in the browser.

```bash
DASH="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/session-dashboard.html"
if [ ! -f "$DASH" ]; then
  echo "Dashboard not found at $DASH — run setup-claude to install it."
  exit 1
fi
if [[ "$OSTYPE" == "darwin"* ]]; then
  open "$DASH"
elif command -v xdg-open &>/dev/null; then
  xdg-open "$DASH"
else
  echo "Open this file in Chrome or Edge: $DASH"
fi
```

After running, tell the user the dashboard is open and they may need to reload
if they want data from the current session (the file picker is persistent across
page loads once granted).
