---
name: apply-ai-improvements
description: >-
  Review pending improvement briefs queued by summarize-ai-usage, brainstorm the
  best approach for each, and apply them to CLAUDE.md, rules, memory, or skill
  spec files. Reads from ~/ClaudeAnalytics/ai-improvements/pending/ if briefs
  exist, otherwise falls back to unapplied findings in the SQLite DB.
user-invocable: true
allowed-tools: Bash, Read, Edit, Write
---

# /apply-ai-improvements — apply queued session improvement briefs

The suggested content is an LLM starting point, not a final answer — read the
existing target file first and adapt.

## Steps

**1. List pending briefs**

```bash
_analytics="${CLAUDE_ANALYTICS_DIR:-$HOME/ClaudeAnalytics}"
ls -t "$_analytics/ai-improvements/pending/"*.md 2>/dev/null || echo "(none)"
```

If briefs exist, skip to step 2.

If none, fall back to the DB:

```bash
python3 - <<'EOF'
import json, os, sqlite3
db = os.path.join(os.environ.get("CLAUDE_ANALYTICS_DIR", os.path.expanduser("~/ClaudeAnalytics")), "session_summaries.db")
con = sqlite3.connect(db)
rows = con.execute(
    "SELECT id, created_at, unapplied_improvements FROM summaries "
    "WHERE unapplied_improvements != '[]' ORDER BY created_at DESC LIMIT 10"
).fetchall()
for row_id, created_at, blob in rows:
    findings = json.loads(blob)
    for f in findings:
        print(f"[summary {row_id} | {created_at[:10]}] ({f.get('confidence','?')}%) "
              f"{f.get('description')} → [{f.get('action_type')}] {f.get('target')}")
        print(f"  content: {(f.get('content') or '')[:120].strip()}")
        print()
con.close()
EOF
```

Review the list with the user. Ask which findings to apply. For each selected
finding, use its `content`, `action_type`, and `target` fields as you would a
brief file — then mark it applied by updating the DB row (remove it from
`unapplied_improvements`, add it to `applied_improvements`):

```bash
python3 - <<'PYEOF'
import json, os, sqlite3
db = os.path.join(os.environ.get("CLAUDE_ANALYTICS_DIR", os.path.expanduser("~/ClaudeAnalytics")), "session_summaries.db")
con = sqlite3.connect(db)
# Replace <ID> and <DESCRIPTION> with actual values
row_id = <ID>
desc = "<DESCRIPTION>"
row = con.execute("SELECT applied_improvements, unapplied_improvements FROM summaries WHERE id=?", (row_id,)).fetchone()
applied = json.loads(row[0])
unapplied = json.loads(row[1])
match = next((f for f in unapplied if f.get("description") == desc), None)
if match:
    unapplied.remove(match)
    applied.append({**match, "result": "applied"})
    con.execute("UPDATE summaries SET applied_improvements=?, unapplied_improvements=? WHERE id=?",
                (json.dumps(applied), json.dumps(unapplied), row_id))
    con.commit()
    print(f"Marked applied: {desc}")
con.close()
PYEOF
```

If nothing in the DB either, stop.

**2. For each brief**

Read it, then check the `suggested_dest` field. If that file exists, read it too
so you can avoid duplication and match its style.

Decide how to apply based on `action_type`:

- **Memory** — write or append to the suggested memory file; add a pointer line
  to `MEMORY.md` in the same directory if the file is new.
- **CLAUDE.md** / **CLAUDE.local.md** — append only the genuinely new guidance,
  wrapped in `<!-- summarize-ai-usage: <description> -->` markers.
- **Rules** — write to `~/.claude/rules/<target>`.
- **Skill/Hook** — the suggested content is a rough spec; use the brainstorming
  skill to design the skill properly before writing anything.
- **Personal learning** — save as a dated markdown file to the Obsidian vault
  (`--obsidian-dir` path if configured, otherwise skip or ask the user for the
  vault path).

**3. Git commit if inside a repo**

For each file you write, find its git root:

```bash
git -C "$(dirname <file>)" rev-parse --show-toplevel 2>/dev/null
```

If that succeeds, stage and commit from the root:

```bash
git -C <root> add <file>
git -C <root> commit -m "$(cat <<'EOF'
chore: apply ai-improvement

Logic:
- Apply improvement finding queued by /summarize-ai-usage

Caveats/assumptions:
- Content is LLM-suggested; verify before committing
EOF
)"
```

If the file is not inside a git repo, skip the commit and log a note.

**4. Move applied briefs to completed**

```bash
_analytics="${CLAUDE_ANALYTICS_DIR:-$HOME/ClaudeAnalytics}"
mkdir -p "$_analytics/ai-improvements/completed"
mv <brief-path> "$_analytics/ai-improvements/completed/"
```

## Principle

The `suggested_content` is a draft. Read the target first. Trim what's already
covered, rewrite what needs context, and skip anything that doesn't fit. A brief
that needs real design work (Skill/Hook especially) should go through the
brainstorming skill rather than being copy-pasted.
