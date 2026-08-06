---
name: writing-field-guides
description: Use when asked to write, extend, or restyle a WP Labs field guide or reference-architecture document — a single-file HTML guide with a cover, a sticky table of contents, numbered sections, SVG and code figures, and collapsible examples. Triggers on "field guide", "reference architecture doc", "write this up as a guide", "document these learnings", or a request to match an existing archetype/field-guide HTML file.
---

# Writing Field Guides

## Overview

A field guide is a **single self-contained HTML file** that states a set of engineering
decisions in general terms, one per numbered section, each closing with the principle behind
it. It is a reference someone returns to, not a narrative of how one project went. The house
style is fixed: same stylesheet, same components, same numbering, so guides read as one series.

Numbering is series-wide (`No. 01`, `No. 02`, ...). Check the existing guides before claiming a
number.

## Workflow

1. **Gather the material first.** A field guide is only worth writing from something that was
   actually built. Read the repo it comes from: README, the modules named in it, the commit
   messages for the decisions and their rejected alternatives, and any review or spec docs. The
   commit bodies are usually the richest source, since they carry the reasoning.
2. **Decide the section list before writing prose.** One decision per section, in the order a
   reader would make them. Group sections (`Foundations`, `Acquisition`, `Safety`, ...) and put
   a `Walkthrough` last. Fifteen to twenty sections is a full guide; eight is a short one.
3. **Copy the template.** `assets/field-guide-template.html` is the boilerplate: head, the
   complete stylesheet, the cover, the sticky TOC, one worked section containing every
   component, the footer, and the scroll-spy script. Never re-author the CSS.
4. **Write the sections.** Generic prose in the section; project-specific names, schemas, and
   code inside `<details class="example">`.
5. **Verify** (see the checklist at the end). Render it and look at it.

## Structure

| Part | Rule |
|---|---|
| Cover `h1` | Short title, one phrase wrapped in `<em>` for the italic |
| Cover `.lede` | Two to four sentences: what the guide is a guide to, then the two or three ideas it rests on, each in `<em>` |
| Cover `.meta` | Three or four fields (Audience, Surface, Status). Status is `For review` until it is not |
| Contents | One `.toc-grid` per group, announced by the inline-styled `h2`. `.num` carries `NN · Group`. Planned sections use `.coming-soon`, which is not a link |
| `aside.toc` | Mirrors the cover groups. Short labels, not full section titles. Every `href` must resolve to a `<section id>` |
| Section 01 | Always `About this guide`: the problem, who the guide is for, what is out of scope, and how to read it |
| Body section | `h2` title, `p.section-lede`, prose with `h3` sub-headings, figures, then a closing `.callout` |
| Last section | A walkthrough that traces one concrete case through every section, with real numbers and back-links |

Every section id is `page-<slug>`, and sections are written adjacent
(`</section><section id="...">`) so the CSS rule that puts a rule line between them applies.

## What to put in a section

- **The decision, not the topic.** "Split by failure mode", not "Pipeline architecture".
- **The reasoning, including what it costs.** A section that only lists benefits is marketing.
  Name the consequence the reader accepts (row count, disk, an attended pipeline).
- **The limits of the control.** If a check resolves DNS once and could be defeated by
  re-resolution, say so in the guide rather than implying the control is total.
- **What is out of scope**, explicitly. Documented, a gap is a known limitation; undocumented,
  it presents as a defect.
- **A closing `.callout`** restating the decision so it survives on its own.

Prefer figures over prose for anything with shape: a pipeline, a set of links between tables, a
specificity ranking, a log excerpt. One figure per idea, numbered `Fig. <section>.<n>`.

## Tone

Follow the repo's output standards (`~/.claude/CLAUDE.md`) and, on top of them, the register of
the existing guides: an internal engineering reference written for architects.

- Declarative and measured. State the decision, then the reasoning.
- No colloquialisms, jokes, or time-of-day asides ("at three in the morning", "loses an
  afternoon", "arms race", "sleeper metric"). No rhetorical questions except as a quoted
  question a reader asks of the data.
- No em-dashes. Recast with a comma, colon, parentheses, or two sentences.
- No negative definition or negative parallelism. "The control is quarantine rather than a more
  sophisticated checker", never "It's not a checker, it's a quarantine".
- No invented specificity ("two hours of work"). Concrete numbers only where they are real.
- `<strong>` marks a defined term on first use. It is not emphasis.
- Contractions: avoid.
- Second person is acceptable for instructions ("Store selectors keyed by their scope").

## Styling

The stylesheet in the template is the house style and is shared across guides. Treat it as
read-only: adding a component means copying an existing one, not writing new CSS.

- Palette: `--accent #005581`, `--ink #2b2b2b`, `--shade #f4f7fa`, `--code-bg #0d1b2a`. Do not
  introduce colours outside the variables.
- Fonts: Source Serif 4 (headings, ledes), Inter Tight (body), JetBrains Mono (labels, code).
  Loaded from Google Fonts; everything else is inline.
- **Self-contained.** No external stylesheet, script, or image. The scroll-spy script is inline
  at the bottom. Do not reference an `assets/toc.js`.
- Components, all in the template: `.callout` (plus `.neutral`, `.preliminary`),
  `figure.code-figure` with `.tok-*` tints, plain `figure` for SVG, `table`,
  `details.example` + `.example-body`, `.two-col` + `.card`, `nav.pager`, `.part-banner`.
- SVG: `viewBox="0 0 760 H"` with `H` trimmed to the content, so the figure has no dead space.
  Use `.svg-label` / `.svg-title` / `.svg-body` / `.svg-mono`, accent fill `#dce9f0` with
  stroke `#005581` for emphasis and `#f4f7fa` / `#d0d7df` for neutral, and an `aria-label`.
- Code figures: escape `&lt;`, `&gt;`, `&amp;`. Keep snippets under about 25 lines and cut them
  down to the point being made; a figure is an illustration, not the source file.

## Where it goes

A guide written up from a project lives in that repo's `.superpowers/` directory (see
`team-docs-convention`), as `<kebab-topic>-field-guide.html`. It is a working document, so do
not commit it unless asked.

## Verification checklist

Run these before calling a guide done:

```bash
python3 - <<'EOF'
import re
h = open('<guide>.html').read()
ids   = set(re.findall(r'<section id="([^"]+)"', h))
hrefs = set(re.findall(r'href="#([^"]+)"', h))
print("dangling hrefs:", sorted(hrefs - ids - {'page-cover'}))
print("unlinked sections:", sorted(ids - hrefs))
for t in ('section','details','figure','table','main','aside','p','li','ol','ul','h2','h3'):
    o, c = len(re.findall(rf'<{t}[ >]', h)), len(re.findall(rf'</{t}>', h))
    if o != c: print(f"MISMATCH {t}: {o} open / {c} close")
print("em-dashes:", h.count('—'))
EOF
```

Then render it and look at it, at 1400px and at 800px:

```bash
cd <dir> && python3 -m http.server 8899   # file:// is blocked in the browser tools
```

- Cover, contents grid, and sticky TOC all render; the TOC highlights the current section on
  scroll.
- Every figure fits its `viewBox` with no large empty band.
- Collapsible examples open and close.
- Section and figure numbers are consecutive, and any count stated in prose ("Seventeen
  decisions") matches the number of sections.
- Below 1000px the sidebar is hidden and nothing scrolls horizontally.
