---
name: queue
description: >-
  Session follow-up backlog. Invoked ONLY by the explicit /queue command — never
  auto-run: `/queue <ask>` captures a follow-up without derailing current work,
  `/queue` (no args / empty args) reviews and runs the backlog after the current task,
  `/queue list` shows it, `/queue migrate` cherry-picks from other sessions.
user-invocable: true
disable-model-invocation: true
argument-hint: "[<ask> | list | migrate | (empty → drain backlog)]"
allowed-tools: Read, Write, Edit, Bash
---

# /queue — session follow-up backlog

Capture follow-up asks or behavior changes mid-task and defer them until the
current work is done, so they never derail the flow in progress. The backlog is
scoped to THIS session (terminal), so parallel sessions keep separate lists.

## Backlog file and helper script

File: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/<session-id>.md`. Derive `<session-id>` from the scratchpad
path in your system prompt (parent-directory name of the scratchpad path, which ends
in `.../<session-id>/scratchpad`).

All file I/O goes through `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q`. Never read or write the queue file
directly — always call the script so format stays consistent.

Item format (for reference only):

```
- [ ] <the ask, verbatim — first line>
  - <sub-bullet if ask was multi-line>
  queued: <YYYY-MM-DD HH:MM:SS>
  completed: <YYYY-MM-DD HH:MM:SS>   ← added by mark-done; open items omit this
  priority: high|med|low             ← optional
  group: <short-name>                ← optional; set at capture or assigned at drain
  ctx: <pwd basename at capture time>
  interpretation: <added at drain time>
```

Cancelled items:

```
- [-] <the ask, verbatim>
  queued: ...
  cancelled: <YYYY-MM-DD HH:MM:SS>
  reason: Moved after clear | Moved after exit | <other>
  moved-to: <uuid | pending>
```

## Mode A — Capture: `/queue [--high|--med|--low] [--group <name>] <ask>` (arguments present)

Single Bash call — no other steps:

```bash
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q add <session-id> [--high|--med|--low] [--group <name>] "<ask verbatim, flags stripped>" "$(pwd)"
```

- Strip `--high`/`--med`/`--low` and `--group <name>` from ARGUMENTS before passing the ask.
- Flags may appear in any order before the ask text.
- If the ask spans multiple lines, pass it quoted with literal newlines — the script
  puts the first line as the item and remaining lines as `  - ` sub-bullets.
- The script prints the acknowledgment. Output nothing else.
- Do NOT start the ask. Return immediately to the current task.

If nothing is currently in progress, say so and offer to run the item now instead.

## Mode B — Drain: bare `/queue` (no arguments)

1. Fetch queue state:
   ```bash
   ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q list <session-id>
   ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q needs-interpretation <session-id>
   ```

2. From the `needs-interpretation` output, generate a detailed `interpretation`
   for each listed item and write it:
   `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q write-interpretation <session-id> <n> "<interpretation>"`
   If no items are listed, skip this step.

2a. **Assign groups** (run after interpretations are written, before triaging):
    - Call `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q list <session-id>` to get current item state.
    - Identify items that do not have a `[group]` badge in the list output.
    - For each ungrouped item, infer a short thematic group name from its ask and interpretation
      (e.g. `ci-fixes`, `queue-ux`, `docs`, `perf`). Then write it:
      `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q write-group <session-id> <n> "<group>"`
    - Show a compact confirmation table:

      | Group | Items |
      |-------|-------|
      | ci-fixes | #1 Fix flaky test, #3 Update CI config |
      | docs | #2 Update readme |

      Ask: "Groups assigned — any changes? Reply `<n> <new-group>` to reassign an item."
    - Apply reassignments via additional `write-group` calls, then proceed to step 3.
    - If all items already have groups (no ungrouped items), skip the confirmation table and
      proceed directly to step 3.

3. Count open items from the list and triage them:
   - **≤ 4 open items**: use `AskUserQuestion` — one **question per item**, all batched into a
     single call (AskUserQuestion supports 1–4 questions). Per-item fields:
     - `header`: `"#N"` + priority badge if set (e.g. `"#3 [H]"`, max 12 chars)
     - `question`: first line of the ask (prefixed with `[group] ` if set), then `Queued: <time>`, then `Intent: <interpretation>`
     - `multiSelect`: false
     - `options`: **always exactly these 3, in this order** (the tool rejects questions with
       fewer than 2 options — never omit or merge any):
       1. label `"Implement"`, description `"Run this item now"`
       2. label `"Keep in queue"`, description `"Leave it for a later session"`
       3. label `"Cancel"`, description `"Drop it"`
     User may attach notes to any selection; a note on **Implement** overrides the item wording.
   - **> 4 open items**: render a markdown table, then ask for disposition.
     Table columns: `#` | `Item / Intent` | `Group` | `Priority`
     - `#`: item number
     - `Item / Intent`: first line of the ask + `—` + the interpretation (one cell, kept brief)
     - `Group`: the item's `group:` field (set in step 2a); blank only if ungrouped after step 2a
     - `Priority`: the item's `priority` field if set, otherwise blank

     After the table, ask:
     "Per item: `<n> implement|queue|cancel [note]`
     Or for a whole group: `<group> implement` / `<group> queue` / `<group> filter`
       - `<group> implement` — run all items in that group
       - `<group> queue`     — keep all items in that group, skip this drain
       - `<group> filter`    — show only that group; re-ask for remaining groups after
     E.g. `ci-fixes implement docs queue 5 cancel`"

4. For all items marked **Implement**, run them in order.
   A per-item note overrides the original wording.
   Treat each as its own task (own commit if it touches code, per the commit policy).
   For items marked **Cancel**, call `q mark-cancelled <session-id> --reason "<reason>" <n>` if
   a reason was given; otherwise `q mark-cancelled <session-id> <n>` (default reason "Cancelled").
   Items marked **Keep in queue** are left untouched.

5. Mark completed: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q mark-done <session-id> <n1> <n2> ...`
   Close with one line: what ran, what was skipped, what was dropped.

6. **Ralph loop**: if open items remain, re-run `q list` and `q needs-interpretation`.
   Loop until no open items or user replies "stop" / "done" / "exit".

## Mode C — List only: `/queue list`

```bash
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q list <session-id>
```

Print the output. Done — produce or write no interpretations.

## Mode D — Migrate: `/queue migrate [<src-session-id>]`

1. Fetch other-session items:
   ```bash
   ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q list-other <session-id>
   ```
   Display the output (each item labelled `[sid8:n]`).
   If a `<src-session-id>` was given in ARGUMENTS, filter the display to that session prefix.

2. Ask: "Which items to migrate? Reply with numbers (e.g. `1 3 5`) or `[sid8:n]` refs.
   `none` or empty to abort."

3. Map plain numbers to the `[sid8:n]` refs from the displayed list.

4. `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q migrate-items <session-id> <sid8:n> [<sid8:n> ...]`

5. Print the output. Done — do NOT auto-drain the backlog afterward.

6. **Assign groups to migrated items** (same flow as Mode B step 2a):
   - Call `q list <session-id>` to identify newly-migrated items lacking a `group:` field.
   - For each ungrouped item, infer a group and call `q write-group <session-id> <n> "<group>"`.
   - Show the confirmation table and apply any reassignments.
   - Skip if all migrated items already have groups.

## Mode E — Clear: `/queue clear`

Cancels all open items in the current session and parks fresh copies in
`pending.md`. The next session's start hook automatically renames
`pending.md` → `<new-session-id>.md`, so the items surface as if they were
queued in the new session.

```bash
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q clear <session-id>
```

Use this when you want to close a session but carry its backlog forward
without running it now. The original items are marked `- [-]` with
`reason: Moved after clear` so the source session's history stays intact.

## See also

- [Using Queue Groups](../../../docs/using-queue-groups.md) — full guide to capturing, assigning, filtering, and bulk-acting on groups
