# Session Summarize

**Goal:** Periodically scan your Claude Code session history, batch-summarize sessions with the Claude CLI, and auto-apply actionable findings (better CLAUDE.md rules, memory updates, skill specs) back into your environment.

## When to use this

- After a multi-session work sprint, to extract what Claude learned that should be permanent
- To build up an improvement log without manual review of every session transcript
- To keep `~/ClaudeAnalytics/session_summaries.db` current for the session dashboard

## Quickstart

Run the skill from any Claude Code session:

```
/session-summarize
```

Or invoke it with `--dry-run` to preview without writing anything:

```
/session-summarize --dry-run
```

## What it does

**Phase 1 — Scan:** Walks `~/.claude/projects/` and computes a SHA-256 for each `.jsonl` session file. Files with an unchanged hash are skipped, so re-runs are fast.

**Phase 2 — Summarize:** Groups new sessions by project and title prefix (up to 10 per batch), builds a structured prompt from each session's tasks, queue items, away summary, and transcript, then calls `claude -p` once per batch. Long transcripts are automatically truncated to first+last 2 turns with an omission marker; sessions that need full context trigger a second call.

**Phase 3 — Apply:** Findings with `confidence > 75` are written immediately:

| action_type | Written to |
|---|---|
| `CLAUDE.md` | Project `CLAUDE.md` (or `~/.claude/CLAUDE.md`) |
| `Rules` | `~/.claude/rules/<target>` |
| `Memory` | `~/.claude/projects/<project>/memory/<target>` + `MEMORY.md` index |
| `Skill/Hook` | `<project-root>/.superpowers/01-specs/<target>` |
| `CLAUDE.local.md` | `<project-root>/CLAUDE.local.md` |

Lower-confidence findings are stored in the `unapplied_improvements` column for manual review — they are never auto-applied.

Applied files are committed automatically:
```
chore: apply session-summarize improvements
```

## Output database

Results are written to `~/ClaudeAnalytics/session_summaries.db` (SQLite). Four tables:

- `sessions` — one row per session file; tracks hash, token counts, cost, titles
- `agents` — subagent spawns extracted from session content
- `summaries` — one row per summarized batch; stores full LLM output and applied/unapplied findings
- `session_summary_items` — many-to-many join between sessions and summaries

## Command-line flags

```bash
python3 session_summarize.py \
  --claude-dir ~/.claude \          # default: ~/.claude
  --sessions-dir ~/.claude/projects \  # default: <claude-dir>/projects
  --output ~/ClaudeAnalytics/session_summaries.db \
  --dry-run                         # skip file writes; DB still updated
```

## Adapting for a team

To run on a schedule (e.g. nightly), invoke the script directly and store the DB file in a shared location (e.g. a network drive or object storage). Do not commit the SQLite binary to git — it has no meaningful merge semantics. Use the `/schedule` skill to set up a cloud agent instead.

To tune the confidence threshold, edit `write_summary()` in `session_summarize.py` — the split between `auto_apply` and `unapplied` is a single comparison against 75.

To add a new `action_type`, extend `_resolve_improvement_dest()` with the new case and update the prompt's enumeration in `LLM_PROMPT_HEADER`.

## Files

```
plugins/wp-labs-sdlc/skills/session-summarize/
├── SKILL.md                         # skill entry point
└── scripts/
    ├── session_summarize.py         # main script
    └── test_session_summarize.py    # 18 unit tests (stdlib unittest)
```
