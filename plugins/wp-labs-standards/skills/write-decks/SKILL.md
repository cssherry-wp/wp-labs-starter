---
name: write-decks
description: >-
  House style for WP Labs slide decks: a single-file 16:9 HTML deck built from a
  deck JSON, with in-file review comments and one-click export to PowerPoint.
  Invoked ONLY by the explicit /write-decks command with a style flag
  (--status, --timeline, --readout) and a source document. Never auto-run.
user-invocable: true
disable-model-invocation: true
---

# Write Decks

## Overview

A deck here is **deck JSON rendered into a self-contained HTML file** by `scripts/build-deck`.
The shell (`assets/deck-shell.html`) carries the whole stylesheet and runtime: keyboard
navigation, data-driven SVG charts, a comment panel that writes comments back into the file,
and an Export button that produces an editable `.pptx` whose slides carry those comments as
PowerPoint review comments. You write the JSON; you never hand-write slide CSS or JS.

A built deck is self-contained: the house faces are embedded (`assets/fonts.css`, regenerate with
`scripts/embed-fonts`), so it renders offline and reports nothing to a third party when a reviewer
opens it. The one exception is the PPTX export, which fetches pptxgenjs on first click, pinned by
an integrity hash.

**The house style is the design brief.** Do not invoke `frontend-design`, restyle slides, or
introduce a palette or typeface of your own: the whole point is that every WP Labs deck looks the
same. Your judgement goes into which content lands on which slide, not into the CSS.

Three outlines share one look. The flag picks the outline; the source document fills it.

```
/write-decks --status   <source>    strategy-day / status readout to sponsors
/write-decks --timeline <source>    phased plan with commercials, risks, references, appendix
/write-decks --readout  <source>    discovery or build readout: method, findings, caveats, next steps
```

`<source>` is any of `.md`, `.txt`, `.html`, `.pptx`, `.docx`. Both are required; ask once if
either is missing.

## Workflow

1. **Extract the source.** `scripts/extract-source <path>` prints plain text (one `## Slide N`
   block per pptx slide, headings kept for docx/html). Read `.md`/`.txt` directly. If the source
   is a dashboard HTML, also note any inline JSON or `loadData()` arrays: they are chart material.
2. **Map source onto the outline** in `references/outlines.md` for the flag. Post a coverage
   table in chat: section · found / thin / missing · where in the source.
3. **Ask about gaps.** One `AskUserQuestion` per group of up to four *required* sections that are
   missing or thin, each with the options: supply content now · skip the slide · leave a `tbd`
   card. Optional sections default to skipped without asking. Ask which tables or dashboard
   tiles should become charts, and what caption each gets, in the same round.
4. **Write `<source-stem>-deck.json`** next to the source, following `references/deck-json.md`.
   Use only the block vocabulary; reach for the `html` escape hatch only when no block fits, and
   keep the section / `data-n` / `.foot` conventions inside it. Cover date is today.
5. **Build**: `scripts/build-deck <deck>.json` writes `<deck>.html` beside it. Rebuilding keeps
   comments already saved in that HTML.
6. **Verify** with the checklist below, then hand over both files. The JSON is the editable
   source; the HTML is what gets circulated.

## Content rules

- One idea per slide; a title states the takeaway, not the topic. Under 25 words in a `lede`.
- Every claim carries a number where the source has one; put it in `<b>`.
- Tables over prose for anything with three or more comparable rows. `best` marks the winner.
- Negative or uncertain findings go in a `callout` with `variant: flag`, never buried.
- Missing required content becomes a `card` with `variant: tbd` naming the owner, so it is
  visible in review and in the export.
- Charts come from data (`chart` block) so they export as native, editable PowerPoint charts;
  use `image` only when no data is recoverable. Values are labelled automatically.
- No client, company, or person names in the template or references; they come from the
  source only.

## Comments and export (for the reader of the deck)

- **Keys**: `←`/`→` move between slides, any digit jumps to a slide number, `O` shows all
  slides, `C` toggles the comment panel, `S` saves the deck (Chrome writes the file in place;
  other browsers download a copy), `Esc` closes the slide overview.
- **Getting around**: the Slides button (or `O`) opens a grid of every slide, with each slide's
  comment count on it; click one to jump. Clicking the slide counter, or typing any digit, jumps
  to a slide by number.
- **Comments**: `C` or the Comments button opens the panel for the current slide. Name is
  asked once and remembered per browser. Comments support replies, edits, deletes. Each change
  is written into the HTML file itself: Chrome asks where to save once (pick the same file),
  other browsers get a "Download updated deck" button. Unsaved changes are also kept in the
  browser and offered back on next open.
- **All comments at once**: the panel header switches between *This slide* and *All*. In *All*,
  comments are grouped by slide and each group heading jumps to its slide, so a reviewer can work
  down the whole deck without hunting for which slides have comments.
- **Commenting on a passage**: highlight text on a slide and a "Comment on selection" button
  appears; the comment then carries that passage as a quote. Clicking the quote in the panel jumps
  to its slide and re-selects the passage, and the quote is carried into the PowerPoint export as
  `Re “…”: comment`. The passage is stored as text, not as a position, so it still resolves
  after the deck is rebuilt; if the wording changed, the deck says the passage is gone rather than
  highlighting the wrong thing.
- **PPTX**: the download button builds the deck with pptxgenjs (loaded from jsDelivr on first
  use, so it needs network) and injects comments as review comments plus speaker notes.
  Print to PDF works from the browser: one slide per page.

## Verification checklist

- `scripts/test-extract-source` and `scripts/test-build-deck` pass (CI runs both).
- Open the built HTML: arrow through every slide; nothing overflows the 1280×720 frame
  (`.body` must not scroll). Print preview shows one slide per page.
- Add a comment, reload from disk, comment is still there.
- Export; open the `.pptx`: slide count matches, charts are editable, comments appear in the
  Comments pane with author names.
- `grep -ri` for any client or person name from the source returns nothing in
  `skills/write-decks/` (the shipped sample uses roles, never names).
