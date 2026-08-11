---
name: unschedule-summarize-ai-usage
description: >-
  Remove the nightly launchd LaunchAgent installed by
  schedule-summarize-ai-usage: unloads com.wp-labs.summarize-ai-usage and
  deletes its plist. Leaves the session_summaries.db and logs in place.
  User-invoked only.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash
---

# /unschedule-summarize-ai-usage — remove the nightly launchd job

```bash
[ "$(uname)" = "Darwin" ] || { echo "This skill only supports macOS (launchd). Detected: $(uname)."; exit 1; }

LABEL="com.wp-labs.summarize-ai-usage"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true

if [ -f "$PLIST" ]; then
  rm "$PLIST"
  echo "Unloaded $LABEL and removed $PLIST."
else
  echo "$PLIST not found — nothing to remove."
fi

echo "session_summaries.db and existing logs are untouched."
```
