---
name: brainstorm-decks
description: >-
  Brainstorm a deck before building it: interviews the user, researches named
  sources per section, and writes a markdown deck source into .superpowers/01-specs,
  then an approved deck source into .superpowers/02-plans for /write-decks (whose
  built JSON and HTML land in .superpowers/03-review).
  Invoked ONLY by the explicit /brainstorm-decks command with a style flag
  (--status, --timeline, --readout). Never auto-run.
user-invocable: true
disable-model-invocation: true
---

# Brainstorm Decks

## Overview

`/write-decks` needs a source document. This skill produces that document when one doesn't exist
yet: it takes the same style flag, walks the matching outline section by section, asks where each
section's content comes from, does the research against those sources, and writes markdown.

Output is markdown, never deck JSON and never HTML. Building the deck is `/write-decks`'s job,
run afterwards on the `02-plans` file.

```
/brainstorm-decks --status   [topic]   strategy-day / sponsor status readout
/brainstorm-decks --timeline [topic]   phased plan (phases, milestones, commercials, risks)
/brainstorm-decks --readout  [topic]   discovery or build readout (method, findings, caveats)
```

**If the flag is missing, print this and stop** — do not guess a flag, do not start reading files:

```
/brainstorm-decks needs a style flag:

  --status    strategy-day / sponsor status readout
  --timeline  phased plan (phases, milestones, commercials, risks)
  --readout   discovery or build readout (method, findings, caveats, next steps)

Example: /brainstorm-decks --timeline VIP supplier support trial
Optional: a topic or an existing rough-notes file to start from.
```

`[topic]` is optional. With no topic, ask for the deck's subject and audience in the first round.

## Paths

Both documents follow `wp-labs-standards:team-docs-convention` — read it, and resolve the repo
root the worktree-safe way it specifies:

- **Working brainstorm:** `<repo-top-level>/.superpowers/01-specs/YYYY-MM-DD-HHmm-<slug>-deck.md`
  — the live document, rewritten as the interview and research progress.
- **Final deck source:** `<repo-top-level>/.superpowers/02-plans/YYYY-MM-DD-HHmm-<slug>-deck.md`
  — written once the user approves the spec. This is the file `/write-decks` consumes.
- **Built deck:** `<repo-top-level>/.superpowers/03-review/` holds the `/write-decks` output,
  `<slug>-deck.json` and `<slug>-deck.html`. Pass that directory to `/write-decks` as the output
  location so the JSON and HTML don't land next to the markdown.

None of these get committed (they are git-ignored working copies). Include a `Model:` line in the
markdown header per `../report-model-provenance.md`.

## Workflow

1. **Load the outline.** Read `../write-decks/references/outlines.md` for the flag. The outline's
   sections are the interview agenda and the document's headings, in order. Also read
   `../write-decks/SKILL.md`'s **Voice** section: the markdown must already be in that voice, or
   `/write-decks` will inherit the slop.
2. **Frame the deck.** One `AskUserQuestion` round: audience and decision the deck is asking for ·
   the one sentence the reader should leave with · date or phase window · whether commercials are
   in scope (for `--timeline`).
3. **Ask for sources, per section.** Required. Post the outline's sections and ask, in rounds of
   up to four, where each section's content comes from. Accept: a file or folder path · a URL ·
   a dashboard or ticket-system export · "ask me, I'll dictate it" · "nothing yet, leave it open".
   Record the answer against every section before researching anything. A section with no named
   source is not researched and not invented — it becomes an open item (below).
4. **Research each section against its own sources only.** Read the paths given; use `WebFetch`
   for URLs the user named. Two hard rules:
   - **Never fill a section from background knowledge.** If the sources don't answer it, the
     section stays open.
   - **Every number carries its provenance inline** — window, denominator, and file or URL, e.g.
     `187 tickets/day (Zendesk export, 16,896 tickets, 25 Mar–23 Jun 2026)`. A number without
     that is not usable in the deck.
   Do not search the open web beyond the sources the user named; ask before widening.
5. **Write the 01-specs document** with one `##` per outline section, in outline order. Each
   section holds the content in deck-ready form (claims with numbers, tables, owner names) plus a
   `Sources:` line listing what it was drawn from. Sections with no source get
   `**OPEN** — needs <what>, from <who>`. End with an `## Open items` list of every OPEN section
   and every unresolved question, each with an owner.
6. **Review with the user.** Show the coverage table (section · sourced / thin / open · source)
   and the open items. Iterate on the 01-specs file until they approve. Keep asking for the
   missing sources rather than writing around a gap.
7. **Write the 02-plans document** on approval: the same content, cleaned to read as a standalone
   deck source, with the open items kept (they become `tbd` cards in the deck, which is the point).
   Then create `.superpowers/03-review/` and tell the user the exact next command:
   `/write-decks <flag> <path-to-02-plans-file>` — and that the built JSON and HTML belong in
   `03-review`.

## Rules

- Markdown only. No deck JSON, no HTML, no slide CSS. Don't pre-empt `/write-decks`.
- The outline is the structure; don't invent sections or reorder them. Optional sections the
  sources don't cover are dropped silently, required ones become OPEN.
- One idea per section heading, stated as a claim in the write-decks Voice, not a topic label.
- Owners are people. Where a section owes work, the name goes in the document or the missing name
  goes in Open items.
- Client and person names come from the user and their sources. Never put a real name in this
  skill's own examples or references.
- Charts: note which tables or exports should become charts and what each caption says, so
  `/write-decks` doesn't have to re-ask.

## Verification checklist

- Both files exist at the `team-docs-convention` paths, resolved from the **main** working tree.
- Every section has either a `Sources:` line or an `OPEN` marker; none has both and none has
  neither.
- Every number in the document names its window and source file or URL.
- `## Open items` lists every OPEN section, each with an owner.
- Neither file is staged or committed.
- The 02-plans file reads as a source document on its own, with no references to this
  conversation ("as discussed", "per your answer").
- `.superpowers/03-review/` exists and is where the built `.json` and `.html` are told to go.
