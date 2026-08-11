# Summarize AI Usage

**Goal:** Periodically scan your Claude Code (and, if present, Pi) session history, batch-summarize sessions with a configurable LLM backend, and auto-apply actionable findings (better CLAUDE.md rules, memory updates, skill specs) back into your environment.

## When to use this

- After a multi-session work sprint, to extract what Claude learned that should be permanent
- To build up an improvement log without manual review of every session transcript
- To keep `~/ClaudeAnalytics/session_summaries.db` current for the session dashboard

## Quickstart

Run the skill from any Claude Code session:

```
/summarize-ai-usage
```

Or invoke it with `--dry-run` to preview without writing anything:

```
/summarize-ai-usage --dry-run
```

## What it does

**Phase 1 — Scan:** Walks `~/.claude/projects/` and computes a SHA-256 for each `.jsonl` session file. If `~/.pi/agent/sessions/` exists (or `--pi-dir` points at one), it's scanned too. Files with an unchanged hash are skipped, so re-runs are fast. Each session's stored path is prefixed with its source (`claude/proj/uuid.jsonl` or `pi/proj/uuid.jsonl`) so the two never collide.

**Phase 2 — Summarize:** Groups new sessions by project, source, and title prefix (up to 10 per batch — a batch never mixes Claude and Pi sessions), builds a structured prompt from each session's tasks, queue items, away summary, and transcript, then calls the chosen summarizer backend once per batch (`--summarizer claude|pi|omlx`, default `claude`). Pi batches use a prompt tuned to local-model concerns (model fit, thinking level, cloud escalation) instead of the Claude Code prompt. Long transcripts are automatically truncated to first+last 2 turns with an omission marker; sessions that need full context trigger a second call.

**Phase 3 — Apply:** Findings with `confidence > 75` are written immediately:

| action_type | Written to |
|---|---|
| `CLAUDE.md` | Project `CLAUDE.md` (or `~/.claude/CLAUDE.md`) |
| `Rules` | `~/.claude/rules/<target>` |
| `Memory` | `~/.claude/projects/<project>/memory/<target>` + `MEMORY.md` index |
| `Skill/Hook` | `<project-root>/.superpowers/01-specs/<target>` |
| `CLAUDE.local.md` | `<project-root>/CLAUDE.local.md` |

Lower-confidence findings are stored in the `unapplied_improvements` column for manual review — they are never auto-applied.

Applied improvement briefs are written to `~/.claude/ai-improvements/pending/`. Run `/apply-ai-improvements` to review each brief and apply it — that skill stages and commits the change when inside a git repo.

Personal learnings (Workflow / Technical / Tooling takeaways) are saved as dated markdown files to your Obsidian vault when `--obsidian-dir` is provided.

## Output database

Results are written to `~/ClaudeAnalytics/session_summaries.db` (SQLite). Four tables:

- `sessions` — one row per session file; tracks hash, token counts, cost, titles, and `source` (`claude` or `pi`)
- `agents` — subagent spawns extracted from session content
- `summaries` — one row per summarized batch; stores full LLM output, applied/unapplied findings, and `source`
- `session_summary_items` — many-to-many join between sessions and summaries

Pi sessions always have a `NULL` cost — there's no pricing model for local models.

## Command-line flags

```bash
python3 summarize_ai_usage.py \
  --claude-dir ~/.claude \          # default: ~/.claude
  --sessions-dir ~/.claude/projects \  # default: <claude-dir>/projects
  --pi-dir ~/.pi/agent/sessions \    # default: ~/.pi/agent/sessions if it exists; pass "" to disable
  --summarizer claude \              # claude | pi | omlx — default: claude
  --output ~/ClaudeAnalytics/session_summaries.db \
  --apply-changes \                 # write briefs + personal learnings
  --obsidian-dir ~/Documents/Obsidian/Learnings \  # save personal learnings here
  --dry-run                         # skip file writes; DB still updated
```

`--model` is passed through to whichever `--summarizer` backend is active. `--summarizer omlx` and `--summarizer pi` read connection/model config from `~/.pi/agent/models.json`.

## Running on a schedule

On macOS, run `/schedule-summarize-ai-usage` to install a launchd LaunchAgent that runs the script directly every night at midnight (no live Claude Code session needed). Remove it with `/unschedule-summarize-ai-usage`. Both are user-invoked only — they make persistent system changes and (on first run) trigger real LLM calls over your full session backlog.

## Adapting for a team

To share results across a team, store the DB file in a shared location (e.g. a network drive or object storage) instead of `~/ClaudeAnalytics/`. Do not commit the SQLite binary to git — it has no meaningful merge semantics.

To tune the confidence threshold, edit `apply_improvements()` in `summarize_ai_usage.py` — the split between queued and unapplied is a single comparison against 75.

To add a new `action_type`, extend `_resolve_improvement_dest()` with the new case and update the prompt's enumeration in `LLM_PROMPT_HEADER` (and `PI_LLM_PROMPT_HEADER` if it should also apply to Pi sessions).

To add another summarizer backend, add a case to `run_summarizer()` in `summarize_ai_usage.py` and extend the `--summarizer` choices in `main()`.

## Dashboard

The session dashboard (`session-dashboard.html`) shows Claude and Pi sessions together. Add a Pi sessions folder with the `⊕ Pi folder` button (appears once a Claude folder is loaded), filter by source with the `Source: All | Claude | Pi` pills in the filter bar, and spot Pi rows by the `Pi` badge next to the model name. Pi rows always show `—` for cost.

## Comparing summarizer models

`compare_models.py` scores summarizer output across models so you can see how a local model stacks up against the Claude default. Run the summarizer once per model into a separate DB named `test_<model>.db` (alongside the default `session_summaries.db`) in your analytics dir, then:

```bash
python3 compare_models.py \
  --analytics-dir ~/ClaudeAnalytics \   # dir holding session_summaries.db + test_*.db
  --default-db ~/ClaudeAnalytics/session_summaries.db \  # scoring reference
  --out ~/ClaudeAnalytics/compare_models/results.json
```

It takes the most recent run day from each DB, restricts to the sessions summarized in *every* DB (fair comparison), fuzzy-diffs each model's array fields (`personal_learnings`, `unapplied_improvements`, tasks, flags) against the default, and scores each model 0–100. Output is `results.json` plus a self-contained `model_comparison_dashboard.html` (the `results.json` is baked into the template). Open the HTML to see a leaderboard and per-dimension matched/extra/missed breakdown. If the default DB is missing, the first `test_*.db` becomes the reference and self-scores near 100% (a warning is printed to stderr).

## Files

```
plugins/wp-labs-sdlc/skills/summarize-ai-usage/
├── SKILL.md                         # skill entry point
├── scripts/
│   ├── summarize_ai_usage.py        # main script
│   ├── compare_models.py            # score summarizer output across models
│   ├── model_comparison_dashboard.html  # comparison dashboard template
│   ├── test_summarize_ai_usage.py   # unit tests (stdlib unittest)
│   └── test_pi_parsing.py           # Pi format detection/parsing tests
└── tests/
    └── test_model_comparison_dashboard.py  # Playwright tests for the comparison dashboard
```
