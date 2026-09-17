# Deck JSON schema

`scripts/build-deck deck.json [out.html]` renders this into the shell. Strings are HTML
fragments: `<b>`, `<i>`, `<br>`, `&middot;`, `&ndash;` are written as-is. `assets/sample-deck.json`
exercises every block and every slide type — `test-build-deck` asserts that, so it stays true.
Run `scripts/build-deck assets/sample-deck.json` to see them all rendered.

```json
{
  "title": "Browser tab title",
  "kicker": "Default cover kicker",
  "footer": "Strictly confidential",
  "slides": [ ...slide objects in order... ]
}
```

## Slides

| `type` | Fields | Renders |
|---|---|---|
| `cover` | `title` (may contain `<br>`), `sub`, `meta` [strings], `kicker` | dark photo/gradient cover |
| `agenda` | `items` [string or `{text, who}`], `eyebrow` | dark numbered agenda |
| `divider` | `title`, `who` | dark section divider |
| `content` (default) | `eyebrow`, `title`, `lede`, `badge`, `blocks` [] | standard slide: eyebrow, title, rule, body |
| `html` | `html` | verbatim `<section class="slide" data-n="NN">…</section>`; keep `data-n` so page numbers and comment keys stay stable (the shell falls back to slide position if you omit it) |

Any slide may set `footer` to override the deck footer. `data-n` is assigned by position.

## Blocks (inside `blocks`)

Each block is an object with one key naming the component, plus optional `style` (inline CSS on
the outer element) where noted.

| Block | Shape | Notes |
|---|---|---|
| `cols` | `{"cols": 2\|3\|4, "blocks": [...], "auto": true}` | grid; `auto:false` lets children fill height (charts) |
| `stack` | `{"stack": [...]}` | plain column wrapper inside `cols` |
| `card` | `{"card": {"title", "items": [...] \| "blocks": [...], "variant": "ok\|warn\|plain\|tbd"}}` | |
| `callout` | `{"callout": {"big", "small", "variant": "flag"}, "style"}` | solid accent block; `flag` = amber negative finding |
| `kpi` | `{"kpi": {"n", "label"}}` | big number |
| `table` | `{"table": {"head": [...], "rows": [[...]], "widths": ["44%", "", "22%"], "best": rowIndex}, "style"}` | first column is always emphasised; a cell starting with `~` renders grey italic |
| `pts` | `{"pts": [...]}` | bullet list |
| `refs` | `{"refs": [...]}` | small numbered list for references |
| `big` | `{"big": [{"h", "s"}]}` | large numbered narrative; five or more items tighten |
| `steps` | `{"steps": [{"title", "text", "items": [...], "who"}]}` | vertical connected timeline; `items` renders bullets under the step title (use instead of a prose `text` when the step is a list of goals), `who` is an optional attribution line — omit it entirely when there is nobody to name |
| `bars` | `{"bars": [{"label", "pct"}]}` | horizontal bars labelled `pct%`; `pct` must be a number |
| `flow` | `{"flow": [{"k", "t"}]}` | left-to-right step boxes with arrows |
| `chips` | `{"chips": [string or {"text", "tag"}]}` | |
| `subhead` / `lede` / `note` | `{"subhead": "..."}` etc. | `note` sits at the column bottom |
| `phaseBand` | `{"phaseBand": [{"name", "note", "flex", "segs": [{"kind": "build\|test\|run", "flex", "label"}]}], "style"}` | proportional gantt band; `flex` must be a number |
| `gate` | `{"gate": {"tag", "text", "risk": false}}` | exit signal / top risk box |
| `claims` | `{"claims": [{"label", "text"}]}` | Claim · Proof · So what rows |
| `chart` | `{"chart": {"type": "bar\|line\|pie\|stackedBar", "labels": [...], "series": [{"name", "values": [...]}], "caption"}}` | SVG in page, native chart in pptx |
| `image` | `{"image": {"src", "alt", "caption"}}` | data: URL or path; exported as picture |
| `html` | `{"html": "..."}` | verbatim fragment |

Status pills inside table cells: `<span class="pill done">Complete</span>`, `pill build`,
`pill scope`, `pill good`, `pill bad`.

There is deliberately no block for a team roster, a money breakdown, or a before/after pair: a
`table`, a row of `card`s, and a `card` of `<code>` items cover all three, and they already
export correctly. Add a block only when the layout cannot be expressed with the ones above.

## Fit rules

A slide is 1280×720 with 52/64 px padding. Rough capacity: 3 cards of 4 bullets plus a callout;
a table of 12 short rows; 6 `steps`; 2 charts side by side. Split rather than shrink.
