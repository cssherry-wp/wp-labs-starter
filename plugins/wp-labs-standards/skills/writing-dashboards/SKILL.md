---
name: writing-dashboards
description: >-
  House style for WP Labs single-file HTML dashboards: a self-contained page
  with a header filter icon summarizing active filters, URL-parameter state
  so a filtered view can be shared as a link, and a sortable table at the
  bottom for drilling into the raw records behind any tile or chart.
  Invoked ONLY by the explicit /writing-dashboards command. Never auto-run:
  use it when asked to build, extend, or restyle a dashboard.
user-invocable: true
disable-model-invocation: true
---

# Writing Dashboards

## Overview

A dashboard here is a **single self-contained HTML file**: no build step, no external
JS/CSS, works from `file://` or a static host. It filters a set of records down to a
view, and every view is two things at once: a URL you can paste into Slack and reopen
to the same filters, and a table at the bottom that lets the reader drop from any
summary straight to the underlying rows. `session-dashboard.html`
(`~/ClaudeAnalytics/session-dashboard.html`) is the reference implementation of this
style; `assets/dashboard-template.html` is the same chrome stripped to a runnable
skeleton over sample data.

## Workflow

1. **Identify the record.** A dashboard is a view over one flat, enumerable thing
   (a session, a ticket, an order). Name its fields before writing markup — they
   become the table columns and the raw dump in the drill-down row.
2. **Copy the template.** `assets/dashboard-template.html` has the header, filter
   icon, URL sync, stats strip, filter bar, and drill-down table already wired
   together over a sample dataset. Never re-author this chrome from scratch.
3. **Replace `loadData()`.** This is the only function tied to a specific data
   source. Point it at a `fetch()`, the File System Access API, or an inline JSON
   blob baked in at build time — whatever fits how the data actually arrives. Every
   other function (filters, `readUrl`/`syncUrl`, table, drill-down) is generic over
   an array of flat objects and does not need to change.
4. **Add filter dimensions.** Each one is a state variable, an entry in
   `activeFilterLines()`, a pill group in `renderFilterBar()`, and a key in
   `readUrl()`/`syncUrl()`. Copy an existing dimension (`category` or `status` in
   the template) rather than inventing a new shape.
5. **Add table columns.** Extend the `cols` array in `renderTable()` and the matching
   `<td>`s in the row template. Leave `insertDetailRow()` dumping the whole record;
   only replace the JSON dump with a richer layout once the schema is stable enough
   to be worth the extra markup.
6. **Verify** (see the checklist at the end). Serve it and click through it.

## Structure

| Part | Rule |
|---|---|
| Header | Title on the left, a `.grow` spacer, then search / filter icon / theme toggle. The spacer is what keeps the filter icon pinned to the upper right regardless of window width |
| Filter icon (`#filterInfo`) | Renders only when a filter is active: a funnel glyph, an active-filter count, and a "clear all" link. Hover shows the list of active filters (`title` attribute is enough; do not build a custom tooltip widget for this alone) |
| URL state | Every filter, the search query, and the sort column/direction round-trip through `readUrl()` / `syncUrl()` via `URLSearchParams` + `history.replaceState`. A filtered view must be copy-pasteable as a link and reopen unchanged |
| Filter bar | One pill group per dimension, `all` first. Clicking a pill sets state, calls `syncUrl()`, then `render()` |
| Drill-down table | Sortable columns (click `<th>`, arrow shows direction), a table-scoped search box, and a click-to-expand detail row under any row showing the full raw record. The point of the table is to be the escape hatch from every rollup above it — never the only way to see the data |
| Stats strip | Optional row of `<span class="sv">value</span> label` pairs above the filter bar, for the two or three numbers a reader checks first |

## What NOT to rebuild per dashboard

Everything in the CSS block, the header markup, `readUrl`/`syncUrl`, `renderFilterInfo`,
`toggleRow`/`insertDetailRow`, and `esc()` is house style shared across every dashboard
built this way. A new dashboard adds a `loadData()`, filter dimensions, and table
columns — nothing else. If a dashboard needs a chart (a timeline, a bar chart, a
sparkline), reach for the `dataviz` skill for how to draw it and which colors to use;
do not invent a new categorical palette here.

## Styling

- Palette and CSS variables in the template match `session-dashboard.html`: dark by
  default, a `prefers-color-scheme: light` block, and `:root[data-theme]` overrides
  for the explicit toggle. Keep all three in sync — see the artifact-design
  theme-awareness rules if extending them.
- Self-contained: no external stylesheet, font, or script. System font stack, inline
  `<style>` and `<script>`.
- Reuse the existing component classes (`.pill`, `.badge`, `.hbtn`, `.sv`/`.sdot`)
  before adding new ones.

## Where it goes

A dashboard built from this template is a working tool, not a document, so it does
not automatically live in `.superpowers/`. Save it wherever the user will actually
open it from (their analytics folder, a repo's `tools/` directory) and confirm the
path with them before writing it there.

## Verification checklist

Run these before calling a dashboard done:

```bash
cd <dir> && python3 -m http.server 8899   # file:// blocks fetch() and the FSA picker in some browsers
```

- The filter icon appears in the upper right only once a filter is active, and
  disappears when "clear all" is clicked.
- Setting a filter, a sort, or a search term updates the URL; reloading that URL
  restores the same view.
- Clicking a table row expands a detail row showing that record's full data; clicking
  it again, or clicking another row, collapses it.
- No unhandled JS console errors (a missing `favicon.ico` 404 is fine to ignore).
- Below the table's `min-width`, the table scrolls horizontally inside `.tbl-wrap`
  rather than the page scrolling.
