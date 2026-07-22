---
name: queue
description: >-
  Session follow-up backlog. Invoked ONLY by the explicit /queue command — never
  auto-run: `/queue <ask>` captures a follow-up without derailing current work,
  `/queue` (no args / empty args) reviews and runs the backlog after the current task,
  `/queue list` shows it, `/queue migrate` cherry-picks from other sessions, and
  `/queue setup` installs a UserPromptSubmit hook so capture and list bypass the LLM.
user-invocable: true
disable-model-invocation: true
argument-hint: "[<ask> | list | migrate | setup | (empty → drain backlog)]"
allowed-tools: Read, Write, Edit, Bash
---

# /queue — session follow-up backlog

Capture follow-up asks or behavior changes mid-task and defer them until the
current work is done, so they never derail the flow in progress. The backlog is
scoped to THIS session (terminal), so parallel sessions keep separate lists.

## Backlog file and helper script

File: `~/.claude/queue/<session-id>.md`. Derive `<session-id>` from the scratchpad
path in your system prompt (parent-directory name of the scratchpad path, which ends
in `.../<session-id>/scratchpad`).

All file I/O goes through `~/.claude/queue/q`. Never read or write the queue file
directly — always call the script so format stays consistent.

Item format (for reference only):

```
- [ ] <the ask, verbatim — first line>
  - <sub-bullet if ask was multi-line>
  queued: <YYYY-MM-DD HH:MM:SS>
  completed: <YYYY-MM-DD HH:MM:SS>   ← added by mark-done; open items omit this
  priority: high|med|low             ← optional
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

## Mode A — Capture: `/queue [--high|--med|--low] <ask>` (arguments present)

If the hook is installed (`~/.claude/queue/hook` exists and is executable), the hook
intercepts this before it reaches the LLM and returns `{"decision":"block"}`. You should
not see this mode. If you do, the block mechanism is not supported — output a note to the
user ("Run `/queue setup` and restart — the hook block mechanism needs adjustment") and
do NOT call `q add` to avoid a duplicate.

If the hook is not installed, fall back to a single Bash call — no other steps:

```bash
~/.claude/queue/q add <session-id> [--high|--med|--low] "<ask verbatim, flag stripped>" "$(pwd)"
```

- Strip `--high`/`--med`/`--low` from ARGUMENTS before passing the ask.
- If the ask spans multiple lines, pass it quoted with literal newlines — the script
  puts the first line as the item and remaining lines as `  - ` sub-bullets.
- The script prints the acknowledgment. Output nothing else.
- Do NOT start the ask. Return immediately to the current task.

If nothing is currently in progress, say so and offer to run the item now instead.

## Mode B — Drain: empty ARGUMENTS

Trigger when invoked with no arguments. Also trigger proactively when the current
task batch is complete (that is the "run after current work" promise).

1. `~/.claude/queue/q needs-interpretation <session-id>` → prints `<n>\t<ask>` for
   each open item missing an `interpretation:`. If output is empty, all items already
   have interpretations — skip to step 3.
2. For each listed item, generate a detailed `interpretation` (scope, files to touch,
   open questions), then write it:
   `~/.claude/queue/q write-interpretation <session-id> <n> "<interpretation>"`
3. `~/.claude/queue/q list <session-id>` — print the full formatted list.
4. **Select items to run:**
   - **≤ 4 open items**: use `AskUserQuestion` (multiSelect) — one option per item
     showing ask + priority badge. Users can attach per-item notes.
   - **> 4 open items**: the numbered list from step 3 is already printed. Ask:
     "Which items to run? Reply with numbers (e.g. 1 3 5) and any per-item notes."
     **Never use `AskUserQuestion` for > 4 items — not even for a subset of them. Always use plain text.**
5. Run chosen items in order. A per-item note overrides the original wording.
   Treat each as its own task (own commit if it touches code, per the commit policy).
6. Mark completed: `~/.claude/queue/q mark-done <session-id> <n1> <n2> ...`
   Close with one line: what ran, what was skipped, what was dropped.
7. **Ralph loop**: if open items still remain, go back to step 1 immediately — do NOT
   wait for another `/queue` invocation. Exit the loop only when no open items remain
   or the user replies with nothing / "stop" / "done" / "exit".

## Mode C — List only: `/queue list`

If the hook is installed, the list is already in your context as `additionalContext` from
the UserPromptSubmit hook. Display that content directly — no Bash call needed.

If the hook is not installed:
```bash
~/.claude/queue/q list <session-id>
```

Print the output. Done — produce or write no interpretations.

## Mode D — Migrate: `/queue migrate [<src-session-id>]`

Trigger when ARGUMENTS starts with `migrate`. Always interactive — list first, then ask.

1. `~/.claude/queue/q list-other <session-id>` — print open items from all other
   sessions, each labelled `[sid8:n]`. If a `<src-session-id>` was given in ARGUMENTS,
   display only shows items from that session (still uses `list-other`, Claude filters
   the display by session prefix).
2. Ask: "Which items to migrate? Reply with numbers (e.g. `1 3 5`) or `[sid8:n]` refs.
   `none` or empty to abort."
3. Map plain numbers to the `[sid8:n]` refs shown in the listing from step 1.
4. `~/.claude/queue/q migrate-items <session-id> <sid8:n> [<sid8:n> ...]`
5. Print the output. Done — do NOT auto-drain the backlog afterward.

## Mode Setup: `/queue setup`

One-time install of the UserPromptSubmit interceptor hook.

After setup:
- **Mode A** (capture) — hook calls `q add` and returns `{"decision":"block"}`, bypassing
  the LLM entirely. Zero latency.
- **Mode C** (list) — hook pre-fetches and injects the list as `additionalContext`; Claude
  just formats and displays it without an extra Bash call.
- Modes B, D — unchanged, go through LLM as before.

Steps:

1. Find the latest non-orphaned `q` and `hook` in the plugin cache. Skip version dirs that
   contain a `.orphaned_at` file. Path pattern:
   `~/.claude/plugins/cache/wp-labs-starter/wp-labs-sdlc/VERSION/skills/queue/{q,hook}`
   Use python3 for semver-aware sort:
   ```bash
   python3 -c "
   import os, glob
   base = os.path.expanduser(os.environ.get('CLAUDE_CONFIG_DIR','~/.claude'))
   for name in ['q','hook']:
       ps = glob.glob(f'{base}/plugins/cache/wp-labs-starter/wp-labs-sdlc/*/skills/queue/{name}')
       ok = [p for p in ps if os.access(p, os.X_OK)
             and not os.path.exists(os.path.dirname(os.path.dirname(os.path.dirname(p)))+'/.orphaned_at')]
       if ok:
           print(name+'='+max(ok, key=lambda p: tuple(int(x) for x in p.split('/')[-4].split('.'))))
   "
   ```

2. Create symlink: `ln -sf <q_path> ~/.claude/queue/q`
   The interceptor uses this stable path at runtime.

3. Copy hook: `cp <hook_path> ~/.claude/queue/hook && chmod +x ~/.claude/queue/hook`

4. Register in `~/.claude/settings.json` (idempotent):
   ```bash
   grep -q 'queue/hook' ~/.claude/settings.json 2>/dev/null && echo "already installed" || \
   jq '.hooks.UserPromptSubmit = [(.hooks.UserPromptSubmit // [])[], \
     {"hooks":[{"type":"command","command":"bash ~/.claude/queue/hook","async":false}]}]' \
     ~/.claude/settings.json > /tmp/q-s.json && mv /tmp/q-s.json ~/.claude/settings.json
   ```

5. Tell the user: "Queue hook installed. Restart Claude to activate. After restart,
   `/queue <text>` captures instantly without LLM."
