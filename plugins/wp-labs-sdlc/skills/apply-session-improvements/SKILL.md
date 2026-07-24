---
name: apply-session-improvements
description: >-
  Review pending improvement briefs queued by session-summarize, brainstorm the
  best approach for each, and apply them to CLAUDE.md, rules, memory, or skill
  spec files. Briefs are in ~/.claude/session-improvements/pending/.
user-invocable: true
allowed-tools: Bash, Read, Edit, Write
---

# /apply-session-improvements — apply queued session improvement briefs

Each brief was written by `/session-summarize --apply-changes` when it found a
high-confidence improvement. The suggested content is an LLM starting point,
not a final answer — read the existing target file first and adapt.

## Steps

**1. List pending briefs**

```bash
ls -t ~/.claude/session-improvements/pending/*.md 2>/dev/null || echo "(none)"
```

If none, stop.

**2. For each brief**

Read it, then check the `suggested_dest` field. If that file exists, read it too
so you can avoid duplication and match its style.

Decide how to apply based on `action_type`:

- **Memory** — write or append to the suggested memory file; add a pointer line
  to `MEMORY.md` in the same directory if the file is new.
- **CLAUDE.md** / **CLAUDE.local.md** — append only the genuinely new guidance,
  wrapped in `<!-- session-summarize: <description> -->` markers.
- **Rules** — write to `~/.claude/rules/<target>`.
- **Skill/Hook** — the suggested content is a rough spec; use the brainstorming
  skill to design the skill properly before writing anything.

**3. Git commit if inside a repo**

For each file you write, find its git root:

```bash
git -C "$(dirname <file>)" rev-parse --show-toplevel 2>/dev/null
```

If that succeeds, stage and commit from the root:

```bash
git -C <root> add <file>
git -C <root> commit -m "chore: apply session-summarize improvement"
```

If the file is not inside a git repo, skip the commit and log a note.

**4. Move applied briefs to done**

```bash
mv <brief-path> ~/.claude/session-improvements/done/
```

## Principle

The `suggested_content` is a draft. Read the target first. Trim what's already
covered, rewrite what needs context, and skip anything that doesn't fit. A brief
that needs real design work (Skill/Hook especially) should go through the
brainstorming skill rather than being copy-pasted.
