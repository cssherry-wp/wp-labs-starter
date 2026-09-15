# Outlines by flag

Required sections are asked about when missing. Optional ones are skipped silently unless the
source has them. Slide types and blocks refer to `deck-json.md`.

## --status (strategy day / sponsor status)

| # | Section | Required | Blocks |
|---|---|---|---|
| 1 | Cover | yes | `cover` |
| 2 | Agenda | yes | `agenda` (dark) |
| 3 | Context / definition | no | `cols 3` of `card` + `callout` |
| 4 | Where we are today | yes | `kpi` + `table` with status pills (`done` `build` `scope`) + `chips` |
| 5 | Completed items | yes | one slide per item or grouped: `card variant ok` with evidence number, or `big` narrative |
| 6 | In progress items | yes | `badge: In progress`, `bars` or `chart` for progress, `card variant warn` for blockers |
| 7 | Evidence | no | `chart`, a `card` of `<code>` before/after items, `flow` |
| 8 | Lessons learned | no | `big` (five) |
| 9 | What we need / next steps | yes | `cols 2` of `card` |

## --timeline (phased plan)

| # | Section | Required | Blocks |
|---|---|---|---|
| 1 | Cover | yes | `cover` |
| 2 | Bottom line | no | `lede` + `cols 4` of `kpi` |
| 3 | Phase band | yes | `phaseBand` (proportional build/test/run segments) |
| 4 | Per-phase one-pager | no | `cols 2`: goal + `pts` workstreams · `chips` timing + `gate` exit + `gate risk` |
| 5 | Milestone / week flow | yes | `steps` with owner per step (split across two columns past six steps) |
| 6 | Deliverables matrix | no | `table`, one column per phase |
| 7 | Team and cadence | no | `table` role · who · commitment, plus `table` cadence · forum · participants · decisions |
| 8 | Commercials | ask | `cols 3` of `card` · `gate` · `card`: per-phase totals either side of the milestone gate |
| 9 | Risks and mitigations | yes | `table` risk · mitigation · owner |
| 10 | Dependencies / out of scope | no | `table` or `pts` |
| 11 | What we need to start | no | `cols 2` of `card` |
| 12 | References | yes | `refs` numbered: source docs, prior decks, dashboards with links |
| 13 | Appendix | no | `divider` then detail slides: full roadmap tables, assumptions, glossary |

Commercials: ask whether to include; internal plans usually skip it.

## --readout (discovery or build readout)

| # | Section | Required | Blocks |
|---|---|---|---|
| 1 | Cover with headline numbers | yes | `cover`; next slide `cols 4` of `kpi` if the source has metrics |
| 2 | Objective and scope | no | `card` what we set out to prove · `card` scope · `card` out of scope |
| 3 | Who we spoke to / method | yes | `table` role · count · side; dataset window and metric definitions in `pts` |
| 4 | Executive summary | yes | `table` scorecard with `best`, `note` for judge/cost caveats |
| 5 | Insights | yes | 2–3 slides of `claims` (Claim · Proof · So what), one number per proof |
| 6 | What changed since last readout | no | `table` topic · before · now |
| 7 | Caveats and what is missing | yes | own slide: `card variant warn` + `callout variant flag` for negative findings |
| 8 | Opportunities | no | `cols 2` (product · tooling) of `card`, `callout` with ranked top three |
| 9 | Path forward | yes | `steps` or `big` numbered next steps with owners; budget line in `note` |

## Charts (any flag)

Any slot may take a `chart` block. Prefer: bar for categories, line for time, stackedBar for
composition across groups, pie only for a single share breakdown of four or fewer parts. Every
chart has a caption `Fig N · what and unit`. Values are labelled automatically.
