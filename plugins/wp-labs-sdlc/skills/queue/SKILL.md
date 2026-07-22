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

**Hook check (run before every mode):** if `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/hook`
does not exist or `queue/hook` is not in `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json`,
prepend your response with:

> Queue hook not installed — capture and list are routed through the LLM (slower).
> Run `/queue setup` and restart to enable instant operation.

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

If the hook is installed (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/hook` exists and is executable), the hook
intercepts this before it reaches the LLM and returns `{"decision":"block"}`. You should
not see this mode. If you do, the block mechanism is not supported — output a note to the
user ("Run `/queue setup` and restart — the hook block mechanism needs adjustment") and
do NOT call `q add` to avoid a duplicate.

If the hook is not installed, fall back to a single Bash call — no other steps:

```bash
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q add <session-id> [--high|--med|--low] "<ask verbatim, flag stripped>" "$(pwd)"
```

- Strip `--high`/`--med`/`--low` from ARGUMENTS before passing the ask.
- If the ask spans multiple lines, pass it quoted with literal newlines — the script
  puts the first line as the item and remaining lines as `  - ` sub-bullets.
- The script prints the acknowledgment. Output nothing else.
- Do NOT start the ask. Return immediately to the current task.

If nothing is currently in progress, say so and offer to run the item now instead.

## Mode B — Drain: bare `/queue` (no arguments)

The hook pre-fetches queue state and injects it as `additionalContext`. Use the injected
data — do not re-run `q list` or `q needs-interpretation`.

1. From the injected "Needing interpretation" section, generate a detailed `interpretation`
   for each listed item and write it:
   `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q write-interpretation <session-id> <n> "<interpretation>"`
   If no items are listed there, skip this step.

2. Count open items from the injected list and triage them:
   - **≤ 4 open items**: use `AskUserQuestion` — one **question per item**, all batched into a
     single call (AskUserQuestion supports 1–4 questions). Per-item fields:
     - `header`: `"#N"` + priority badge if set (e.g. `"#3 [H]"`, max 12 chars)
     - `question`: first line of the ask, then `Queued: <time>`, then `Intent: <interpretation>`
     - `multiSelect`: false
     - `options`: **always exactly these 3, in this order** (the tool rejects questions with
       fewer than 2 options — never omit or merge any):
       1. label `"Implement"`, description `"Run this item now"`
       2. label `"Keep in queue"`, description `"Leave it for a later session"`
       3. label `"Cancel"`, description `"Drop it"`
     User may attach notes to any selection; a note on **Implement** overrides the item wording.
   - **> 4 open items**: print the list (already in context) and ask:
     "For each item reply: `<n> implement|queue|cancel [note]`. E.g. `1 implement 2 cancel`."

3. For all items marked **Implement**, run them in order.
   A per-item note overrides the original wording.
   Treat each as its own task (own commit if it touches code, per the commit policy).
   For items marked **Cancel**, call `q mark-cancelled <session-id> --reason "<reason>" <n>` if
   a reason was given; otherwise `q mark-cancelled <session-id> <n>` (default reason "Cancelled").
   Items marked **Keep in queue** are left untouched.

4. Mark completed: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q mark-done <session-id> <n1> <n2> ...`
   Close with one line: what ran, what was skipped, what was dropped.

5. **Ralph loop**: if open items remain, call `q list` and `q needs-interpretation` directly
   (hook only pre-fetches on the initial `/queue` prompt). Loop until no open items or user
   replies "stop" / "done" / "exit".

## Mode C — List only: `/queue list`

If the hook is installed, it returns `{"decision":"block"}` with the list output directly —
Claude is never invoked. You should not see this mode. If you do, the hook is not active.

If the hook is not installed:
```bash
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q list <session-id>
```

Print the output. Done — produce or write no interpretations.

## Mode D — Migrate: `/queue migrate [<src-session-id>]`

The hook pre-fetches `q list-other` and injects as `additionalContext`. Use that data.

1. Display the injected list of other-session items (each labelled `[sid8:n]`).
   If a `<src-session-id>` was given in ARGUMENTS, filter the display to that session prefix.

2. Ask: "Which items to migrate? Reply with numbers (e.g. `1 3 5`) or `[sid8:n]` refs.
   `none` or empty to abort."

3. Map plain numbers to the `[sid8:n]` refs from the displayed list.

4. `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q migrate-items <session-id> <sid8:n> [<sid8:n> ...]`

5. Print the output. Done — do NOT auto-drain the backlog afterward.

## Mode Setup: `/queue setup`

One-time install of the UserPromptSubmit interceptor hook.

After setup, all `/queue` commands route through the hook first:
- **Mode A** (capture) — hook calls `q add`, blocks LLM. Zero latency.
- **Mode B** (drain) — hook pre-fetches queue state, injects as context, LLM handles selection/execution.
- **Mode C** (list) — hook calls `q list`, blocks LLM, shows output directly.
- **Mode D** (migrate) — hook pre-fetches `q list-other`, injects as context, LLM handles selection.

Steps:

1. Find the latest non-orphaned `q` and `hook` in the plugin cache. Skip version dirs that
   contain a `.orphaned_at` file. Path pattern:
   `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/wp-labs-starter/wp-labs-sdlc/VERSION/skills/queue/{q,hook}`
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

2. Create symlink: `ln -sf <q_path> ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/q`
   The interceptor uses this stable path at runtime.

3. Copy hook: `cp <hook_path> ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/hook && chmod +x ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/hook`

4. Register in `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json` (idempotent — remove existing entry first, then add fresh):
   ```bash
   jq '.hooks.UserPromptSubmit = (
     [(.hooks.UserPromptSubmit // [])[] |
       select((.hooks // []) | map(.command // "" | contains("queue/hook")) | any | not)]
     + [{"hooks":[{"type":"command","command":"bash ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/queue/hook","async":false}]}]
   )' "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json" > /tmp/q-s.json && \
   mv /tmp/q-s.json "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
   ```

5. Tell the user: "Queue hook installed. Restart Claude to activate. After restart,
   `/queue <text>` captures instantly without LLM."
