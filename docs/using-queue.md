# Using /queue

`/queue` is a session-scoped follow-up backlog. Capture ideas, fixes, or behavior changes mid-task so they don't derail what you're doing — then run them all at once when you're ready.

The backlog is per terminal session, so parallel Claude Code windows keep separate lists.

## Quick reference

| Invocation | What it does |
|---|---|
| `/queue <ask>` | Capture a follow-up (Mode A) |
| `/queue [--high\|--med\|--low] [--group <name>] <ask>` | Capture with priority/group |
| `/queue` | Review and run the backlog (Mode B — drain) |
| `/queue list` | Print the backlog without acting (Mode C) |
| `/queue migrate [<session-id>]` | Cherry-pick items from another session (Mode D) |
| `/queue clear` | Cancel open items and carry them to the next session (Mode E) |

## Capturing items (Mode A)

While Claude is mid-task, capture a follow-up without interrupting the current work:

```
/queue Fix the flaky auth test
/queue --high Investigate the memory spike on prod
/queue --group docs Update the onboarding README
```

Claude writes the item to the backlog and returns immediately to the current task. The item is stored in `~/.claude/queue/<session-id>.md`.

**Priority flags** (`--high`, `--med`, `--low`) mark urgency. **`--group <name>`** tags the item for bulk triage — see [Using Queue Groups](using-queue-groups.md).

## Draining the backlog (Mode B)

Run `/queue` with no arguments to work through the list:

1. Claude writes an interpretation for each item (what it means in context).
2. Groups are inferred and confirmed (see [Using Queue Groups](using-queue-groups.md)).
3. For ≤ 4 items: a per-item prompt asks **Implement / Keep in queue / Cancel**.
   For > 4 items: a summary table with group/priority columns, then a text prompt for dispositions.
4. Chosen items run in order, each as its own task (own commit if it touches code).
5. Any remaining open items trigger another drain loop until the queue is empty or you say "stop".

## Listing without acting (Mode C)

```
/queue list
```

Prints the current session's backlog. No interpretations are written, nothing runs.

## Migrating from another session (Mode D)

```
/queue migrate
```

Shows open items from all other sessions, lets you pick which to pull into the current session. The source items are marked cancelled with a "moved" reason; the copies appear as fresh items here. Useful when you switch terminals mid-project.

Pass a session ID prefix to filter: `/queue migrate abc12345`.

## Carrying items to the next session (Mode E)

```
/queue clear
```

Cancels all open items in the current session and parks fresh copies in `pending.md`. The next session's start hook automatically renames `pending.md` → `<new-session-id>.md`, so the items surface as if queued in the new session. Use this to close a session cleanly without losing work.

## Groups

Tag items at capture time or let Claude infer them at drain time. Groups let you bulk-act on a theme (`ci-fixes implement`) instead of deciding item-by-item.

Full guide: [Using Queue Groups](using-queue-groups.md)
