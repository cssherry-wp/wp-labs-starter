---
name: session-summarize
description: >-
  Scan Claude Code session JSONL files, batch-summarize them via the claude CLI,
  and write results to a SQLite database. Pass --apply-changes to queue
  high-confidence improvement findings as briefs for /apply-session-improvements.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash
---

# /session-summarize — summarize sessions and queue improvements

Run the session summarizer. It scans `~/.claude/projects/` for new or changed
session JSONL files, groups them by project, calls `claude -p` to summarize
each batch, and writes results to `~/ClaudeAnalytics/session_summaries.db`.

By default, improvement findings are stored as unapplied in the DB only.
Pass `--apply-changes` to write high-confidence findings (confidence > 75) as
brief files to `~/.claude/session-improvements/pending/`, then run
`/apply-session-improvements` to review and apply them with proper brainstorming.

```bash
python3 "$(dirname "$0")/scripts/session_summarize.py" \
  --claude-dir "${CLAUDE_CONFIG_DIR:-$HOME/.claude}" \
  --output "$HOME/ClaudeAnalytics/session_summaries.db" \
  "$@"
```
