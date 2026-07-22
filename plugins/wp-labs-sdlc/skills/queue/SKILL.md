---
name: queue
description: >-
  Session follow-up backlog. Invoked ONLY by the explicit /queue command — never
  auto-run: `/queue <ask>` captures a follow-up without derailing current work,
  `/queue` (no args / empty args) reviews and runs the backlog after the current task, and
  `/queue list` shows it. The point is non-disruptive capture now, deferred
  execution later.
user-invocable: true
disable-model-invocation: true
argument-hint: "[<ask> | list | (empty → drain backlog)]"
allowed-tools: Read, Write, Edit, Bash
---

# /queue — session follow-up backlog

Capture follow-up asks or behavior changes mid-task and defer them until the
current work is done, so they never derail the flow in progress. The backlog is
scoped to THIS session (terminal), so parallel sessions keep separate lists.

## Backlog file (per session)

Use `~/.claude/queue/<session-id>.md`. Derive `<session-id>` from this session's
scratchpad path in your system prompt — it ends in `.../<session-id>/scratchpad`,
so the id is that path's parent-directory name (a UUID). Reading the id from the
scratchpad path keeps the backlog scoped to THIS session/terminal, while storing
the file under `~/.claude` (persistent config) rather than the OS temp dir. Run
`mkdir -p ~/.claude/queue` and create the file if it doesn't exist.

<!-- ponytail: the session id still comes from the scratchpad path, but the file
     lives in ~/.claude, so it survives /private/tmp cleanup and reboots that
     would eventually reap the scratchpad. Per-session isolation is unchanged. -->

Each item is one block. Capture writes the first three (or four) lines; the
`interpretation` line is added later, at drain/list time (see Mode B/C):

```
- [ ] <the ask, verbatim>
  queued: <YYYY-MM-DD HH:MM:SS>
  priority: high|med|low   ← optional; omit when no flag was given
  ctx: <one line on what was being worked on when it was added>
  interpretation: <added at drain/list — your detailed reading of the ask:
    what it requires, the scope, the files/areas it will touch, open questions>
```

Cancelled items use `- [-]` and gain a `reason:` field:

```
- [-] <the ask, verbatim>
  queued: <YYYY-MM-DD HH:MM:SS>
  reason: Moved after clear | Moved after exit | <other>
  moved-to: <uuid | pending>   ← include when moved to another session
```

## Mode A — Capture: `/queue [--high|--med|--low] <ask>` (arguments present)

**Priority flags** (optional): if ARGUMENTS begins with `--high`, `--med`, or `--low`,
strip the flag, record it as `priority:`, and use the remaining text as the ask.
`/queue --high fix the login crash` → priority: high, ask: "fix the login crash".

Keep this near-instant so it does not disrupt the current flow. Use **one single
Bash call** — timestamp + append + acknowledgment together, so the item hits disk
before any other tool runs:

```bash
FILE=~/.claude/queue/<session-id>.md
STAMP=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p ~/.claude/queue
# With priority (example for --high):
printf -- '- [ ] <ask verbatim>\n  queued: %s\n  priority: high\n  ctx: <one line on current work>\n\n' "$STAMP" >> "$FILE"
# Without priority:
printf -- '- [ ] <ask verbatim>\n  queued: %s\n  ctx: <one line on current work>\n\n' "$STAMP" >> "$FILE"
printf 'Queued (%d in backlog) → %s\n' "$(grep -c '^\- \[' "$FILE")" "$FILE"
```

Rules:
- Store the user's exact wording (flag stripped) as the `- [ ] ` item. Do **not** summarize.
- Do **not** write an `interpretation` — it is added at drain/list time.
- Output **no prose text** — the Bash tool result IS the notification.
- Do NOT start the ask, and do NOT re-plan current work around it. Return immediately.

If nothing is currently in progress, say so and offer to run the item now
instead of queueing it.

## Mode B — Drain (review + run): empty ARGUMENTS

Trigger when: the skill is invoked with **no arguments** (ARGUMENTS is empty or
whitespace-only) — whether typed as `/queue`, as a bare skill name, or any other
invocation that passes no text. Also trigger **proactively the moment the current
task batch is complete** (that is the "run after current work" promise).

1. Read the backlog. If there are no open items, say so and stop.
2. For each open item, produce its **detailed `interpretation`** now (this is
   the point where reading scope/files/open-questions is appropriate) and write
   it back into the item block if not already present.
3. **Sort open items by priority before listing**: high → med → low → unset.
   List every open item, numbered in sorted order, showing a priority badge
   (`[H]` / `[M]` / `[L]` — omit when no priority set), the **verbatim ask,
   its `queued` date-time, and its `interpretation`**.
4. Ask the user which to proceed with. They can pick any subset, skip the rest,
   and attach a note to any item — a changed instruction, "just tell me about
   it, don't change anything", or "drop this one". Use `AskUserQuestion`
   (multiSelect) when there are ≤ 4 items; for more, list them in prose and ask
   the user to reply with the numbers to run plus any per-item notes.
5. Run the chosen items in listed order. A per-item note **overrides** the
   original wording. An item flagged as information-only gets an answer, not a
   code change. Treat each as its own task (own commit if it touches code, per
   the commit policy).
6. Update the backlog:
   - Run items → mark `- [x]` (keep their `queued`/`interpretation`).
   - **Un-selected (skipped) items STAY on the queue, open and unchanged** —
     skipping is not dropping.
   - Remove an item only when the user explicitly says to drop it.
   Close with one line: what ran, what was skipped (still queued), what was
   dropped.
7. **Loop (ralph loop)**: after step 6, if open items still remain, immediately
   return to step 2 (re-read, re-sort, re-list with full interpretation, ask
   again) — do NOT wait for another `/queue` invocation. Repeat until:
   - no open items remain, or
   - the user replies with nothing, "stop", "done", or "exit".

## Mode C — List only: `/queue list`

Print the open backlog items, numbered, each with its `queued` date-time and a
detailed `interpretation` (produce it now if the item has none yet, and write it
back). Change nothing else.

## Mode D — Clear: `/queue clear`

Park all open items for the next session. Use when ending work mid-backlog.

1. Read the current session's queue file. If no open `- [ ]` items, say so and stop.
2. For each open item, rewrite `- [ ]` → `- [-]` and insert `  reason: Moved after clear`
   on the line after `queued:` (or after `priority:` if present). Append
   `  moved-to: pending` as the last field of the block.
3. Write those items as **fresh `- [ ]` blocks** (no `reason:`, no `moved-to:`) to
   `~/.claude/queue/pending.md`. Prepend: `# Pending from <session-id> <YYYY-MM-DD>`.
   Overwrite if `pending.md` already exists.
4. Acknowledge: "Cleared N items — parked in pending.md for next session."

The SessionStart hook detects `pending.md` on the next session start and renames
it to `~/.claude/queue/<new-session-uuid>.md` automatically.
