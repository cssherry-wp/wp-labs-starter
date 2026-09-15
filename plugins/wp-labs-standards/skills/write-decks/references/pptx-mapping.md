# HTML → PowerPoint export mapping

Lives in the `<script>` of `assets/deck-shell.html`. Geometry comes from the browser: each slide is
forced visible and unscaled, then `getBoundingClientRect()` / `getComputedStyle()` decide position,
size, colour, and font. `LAYOUT_WIDE` (13.33×7.5 in) equals 1280×720 px at 96 dpi; px/96 = in,
px×0.75 = pt.

| DOM | Emitter | pptxgenjs |
|---|---|---|
| `section.slide` | `exportSlide` | `addSlide`, background colour (`001E2E` for cover/dark/divider), data-URL photo if the CSS var holds one, page number from `::after` |
| `figure.chart[data-chart]` | `chart` | `addChart` bar / line / pie / stacked, palette from `--accent` ramp, value labels on |
| `img`, inline `svg` | `image`, `svgImage` | rasterised to PNG on a canvas, `addImage` |
| `table` | `table` | `addTable`, column widths from header cells, bottom hairlines |
| `ol.agenda` | `numbered` | number · text · timing as three centred boxes per row plus a rule |
| `ol.big`, `ol.steps` | `numbered` | explicit counter text or circle, then children |
| other `ul`/`ol` | `list` | one `addText` with bullet runs |
| element with background or border | `box` | `addShape(rect)` fill, one `line` per visible border side |
| element whose children are all inline | `text` | `addText` with bold/italic/`<br>` runs |
| mixed element | `shallowText` + recurse | own text nodes measured with a `Range`, block children walked |

Fonts map to Georgia (serif), Courier New (mono), Calibri (sans) so the file opens without
substitution prompts — the exported deck therefore does not match the HTML's own faces, which are
embedded rather than mapped. `fit: shrink` keeps text inside its measured box.

## Comments

`addNotes` always gets `[author date] text` per comment (replies prefixed `Re [author]:`, and a
comment made on a highlighted passage prefixed `Re “passage”:`).
pptxgenjs is loaded from jsDelivr on first export, pinned by the `PPTX_SRI` integrity hash in
the shell: bump that hash whenever `PPTX_URL`'s version changes or the browser will refuse the
script and export will fail.

When any comment exists, `injectComments` reopens the pptx zip with the bundled JSZip and adds
legacy review comments: `ppt/commentAuthors.xml`, `ppt/comments/commentN.xml` per slide,
relationships in `ppt/_rels/presentation.xml.rels` and `ppt/slides/_rels/slideN.xml.rels`, and
two `Override` content types. PowerPoint 2016+ opens these and upgrades them on save.

`window.deckSelfTest()` in the console exports the current deck and returns
`{slides, commentParts, ok, base64}`; `ok` asserts slide count and comment part wiring.
