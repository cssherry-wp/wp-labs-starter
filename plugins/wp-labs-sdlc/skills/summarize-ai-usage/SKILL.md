---
name: summarize-ai-usage
description: >-
  Scan Claude Code and Pi session JSONL files, batch-summarize them via the
  claude CLI, pi CLI, or an omlx endpoint, and write results to a SQLite
  database. Pass --apply-changes to queue high-confidence improvement
  findings as briefs for /apply-ai-improvements.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash
---

# /summarize-ai-usage — summarize sessions and queue improvements

Run the session summarizer. It scans `~/.claude/projects/` for Claude Code sessions
and `~/.pi/agent/sessions/` for Pi sessions (auto-discovered if the path exists),
groups them by project and source, calls the chosen summarizer backend to summarize
each batch, and writes results to `$CLAUDE_ANALYTICS_DIR/session_summaries.db`
(default: `~/ClaudeAnalytics/`).

Pass `--pi-dir ""` to explicitly disable Pi scanning. Pass `--pi-dir PATH` to point
at a non-default Pi sessions directory.

Use `--summarizer pi` or `--summarizer omlx` to run summarization via the Pi CLI or
an omlx-compatible endpoint (reads `~/.pi/agent/models.json` for connection config).
The `--model` flag is passed to whichever backend is active.

Briefs, trimmed sessions, and other artifacts go to the same directory as the
DB (`--output`'s parent). Override the DB location with `--output` to relocate
all outputs together; use `--archive-dir` to override only the trimmed-session
directory independently.

By default, improvement findings are stored as unapplied in the DB only.
Pass `--apply-changes` to write high-confidence findings (confidence > 75) as
brief files to `<output-dir>/ai-improvements/pending/`, then run
`/apply-ai-improvements` to review and apply them with proper brainstorming.

Pass `--obsidian-dir <path>` together with `--apply-changes` to also save
personal learnings as dated markdown files to your Obsidian vault.

**New flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--pi-dir PATH` | `~/.pi/agent/sessions` | Pi sessions root. Skipped if path absent. Pass `""` to disable. |
| `--summarizer {claude,omlx,pi}` | `claude` | Backend for summarization prompts. |

```bash
python3 "$(dirname "$0")/scripts/summarize_ai_usage.py" \
  --claude-dir "${CLAUDE_CONFIG_DIR:-$HOME/.claude}" \
  --output "$HOME/ClaudeAnalytics/session_summaries.db" \
  "$@"
```

To compare summarizer output across models, run the summarizer once per model
into `test_<model>.db` files, then score them with
`scripts/compare_models.py` (writes `results.json` + a comparison dashboard).
See [`docs/summarize-ai-usage.md`](../../../../docs/summarize-ai-usage.md) for details.
