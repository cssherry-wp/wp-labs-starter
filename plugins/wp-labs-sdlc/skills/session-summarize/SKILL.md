---
name: session-summarize
description: >-
  Scan Claude Code session JSONL files, batch-summarize them via the claude CLI,
  write results to a SQLite database, and auto-apply improvement findings to
  CLAUDE.md, rules, memory, and skill spec files. Run periodically to build up
  an improvement log from past sessions.
user-invocable: true
allowed-tools: Bash
---

# /session-summarize — summarize sessions and apply improvements

Run the session summarizer. It scans `~/.claude/projects/` for new or changed
session JSONL files, groups them by project, calls `claude -p` to summarize
each batch, and writes results to `~/ClaudeAnalytics/session_summaries.db`.

Findings with confidence > 75 are auto-applied to CLAUDE.md, rules, memory,
or skill spec files. Lower-confidence findings are stored for manual review.

```bash
python3 "$(dirname "$0")/scripts/session_summarize.py" \
  --claude-dir "${CLAUDE_CONFIG_DIR:-$HOME/.claude}" \
  --output "$HOME/ClaudeAnalytics/session_summaries.db" \
  "$@"
```

Pass `--dry-run` to preview what would be written without making any changes
(the DB is still updated on dry runs).
