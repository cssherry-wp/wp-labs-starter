---
name: schedule-summarize-ai-usage
description: >-
  Install a macOS launchd LaunchAgent that runs summarize-ai-usage nightly at
  midnight, so session history keeps getting summarized without a live Claude
  Code session open. Writes ~/Library/LaunchAgents/com.wp-labs.summarize-ai-usage.plist
  and loads it. User-invoked only — this makes a persistent system-level
  change and real LLM calls on its own schedule, so it must not run without
  being asked.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash
---

# /schedule-summarize-ai-usage — nightly launchd job for summarize-ai-usage

macOS only (launchd). Resolves real binary paths rather than relying on shell
rc files, since launchd runs jobs outside any login/interactive shell — a
`claude` or `python3` defined only via a shell function or a PATH edit in
`.zshrc` (interactive-only) won't be found otherwise.

```bash
set -e

[ "$(uname)" = "Darwin" ] || { echo "This skill only supports macOS (launchd). Detected: $(uname)."; exit 1; }

PYTHON_BIN=""
for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  [ -x "$p" ] && PYTHON_BIN="$p" && break
done
if [ -z "$PYTHON_BIN" ]; then
  CANDIDATE="$(command -v python3 || true)"
  case "$CANDIDATE" in
    */shims/*) ;; # pyenv/rbenv/asdf shim — depends on env vars launchd won't have; skip it
    *) PYTHON_BIN="$CANDIDATE" ;;
  esac
fi
[ -n "$PYTHON_BIN" ] || { echo "Could not find a real (non-shim) python3. Checked /opt/homebrew/bin, /usr/local/bin, /usr/bin, and PATH."; exit 1; }

CLAUDE_BIN="$(which claude 2>/dev/null || true)"
if [ -z "$CLAUDE_BIN" ]; then
  for c in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
    [ -x "$c" ] && CLAUDE_BIN="$c" && break
  done
fi
[ -n "$CLAUDE_BIN" ] || { echo "Could not locate the claude binary (checked PATH and common install dirs). Install it or add it to PATH, then retry."; exit 1; }

# Resolve the summarize-ai-usage script: prefer the main repo checkout over a
# worktree (worktrees get deleted after merge, breaking the scheduled job).
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  MAIN_ROOT="$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)"
  SCRIPT="$MAIN_ROOT/plugins/wp-labs-sdlc/skills/summarize-ai-usage/scripts/summarize_ai_usage.py"
else
  SCRIPT="$(cd "$(dirname "$0")/../summarize-ai-usage/scripts" && pwd)/summarize_ai_usage.py"
fi
[ -f "$SCRIPT" ] || { echo "summarize_ai_usage.py not found at $SCRIPT"; exit 1; }

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
ANALYTICS_DIR="${CLAUDE_ANALYTICS_DIR:-$HOME/ClaudeAnalytics}"
DB_PATH="$ANALYTICS_DIR/session_summaries.db"
LOG_PATH="$ANALYTICS_DIR/logs/summarize-ai-usage.log"
JOB_PATH_ENV="$(dirname "$CLAUDE_BIN"):$(dirname "$PYTHON_BIN"):/usr/bin:/bin:/usr/sbin:/sbin"

LABEL="com.wp-labs.summarize-ai-usage"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

# A machine may keep more than one Claude config dir (separate profiles or
# clients), each with its own sessions. A job that scans only the primary one
# silently misses the rest, so every sibling config dir found is appended to the
# comma-separated --claude-dir list. Detected rather than hardcoded, so this is a
# no-op where no siblings exist.
CLAUDE_DIRS="$CLAUDE_DIR"
for d in "$HOME"/.claude*/; do
  d="${d%/}"
  [ -d "$d/projects" ] || continue
  [ "$d" = "$CLAUDE_DIR" ] && continue
  CLAUDE_DIRS="$CLAUDE_DIRS,$d"
  echo "Also scanning: $d"
done

mkdir -p "$(dirname "$LOG_PATH")" "$(dirname "$PLIST")"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$LABEL</string>
	<key>ProgramArguments</key>
	<array>
		<string>$PYTHON_BIN</string>
		<string>$SCRIPT</string>
		<string>--claude-dir</string>
		<string>$CLAUDE_DIRS</string>
		<string>--output</string>
		<string>$DB_PATH</string>
	</array>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>$JOB_PATH_ENV</string>
		<key>HOME</key>
		<string>$HOME</string>
	</dict>
	<key>StartCalendarInterval</key>
	<dict>
		<key>Hour</key>
		<integer>0</integer>
		<key>Minute</key>
		<integer>0</integer>
	</dict>
	<key>StandardOutPath</key>
	<string>$LOG_PATH</string>
	<key>StandardErrorPath</key>
	<string>$LOG_PATH</string>
	<key>RunAtLoad</key>
	<false/>
</dict>
</plist>
PLIST

plutil -lint "$PLIST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo
echo "Installed and loaded $LABEL — fires nightly at 00:00 local time."
echo "  Script:  $SCRIPT"
echo "  DB:      $DB_PATH"
echo "  Log:     $LOG_PATH"
echo
echo "Caveats:"
echo "- If the Mac is fully off at midnight, that night is skipped (no catch-up run)."
echo "  If merely asleep, macOS wakes briefly to run scheduled launchd jobs."
echo "  Either way, sessions are hashed and skipped once summarized, so a missed"
echo "  night is absorbed on the next successful run."
echo "- Does not pass --apply-changes, so it only builds up the DB — it will not"
echo "  edit CLAUDE.md, rules, or memory files unattended."
echo "- The first run summarizes your full backlog of un-summarized sessions,"
echo "  which can mean many real 'claude -p' calls. To remove this schedule,"
echo "  run /unschedule-summarize-ai-usage."
```
