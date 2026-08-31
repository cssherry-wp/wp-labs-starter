# Superpowers Progress Notes

**Goal:** Make specs, plans, and review documents record their own lifecycle, so their history is
readable from the file alone — on any machine, since each note syncs to the
[superpowers sidecar](superpowers-sidecar.md) as it is written.

## 1. What gets recorded, and where

Three notes, each written by the skill that causes the transition:

- **`Promoted to plan:` in the spec** — written by `writing-plans` after the plan is saved:

  ```
  Promoted to plan: .superpowers/02-plans/2026-08-31-0323-skill-progress-notes.md (2026-08-31 03:30)
  ```

- **`Implemented:` in the plan** — written by `executing-plans` or
  `subagent-driven-development`, whichever one finishes the plan, once every task is done and
  tests pass:

  ```
  Implemented: 2026-08-31 18:05
  ```

- **`## Disposition` in the review** — written by `change-review` after interactive triage,
  listing every finding's current outcome:

  ```markdown
  ## Disposition

  _Updated 2026-08-31 14:22_

  - CR-001: fixed
  - CR-003: queued — revisit after the perf work lands
  - CR-005: ignored — intentional, mirrors the upstream behaviour
  - CR-007: logged — #142
  ```

These are notes in the document itself — separate from the GitHub/Jira tracker sync described in
`team-docs-convention`'s lifecycle section.

## 2. Reading a document's history

Open the file:

- A spec with no `Promoted to plan:` line was never turned into a plan (or the plan session hasn't
  finished yet). One with the line points at the exact plan file.
- A plan with no `Implemented:` line is still open, abandoned, or was executed by a session that
  never reached the finish step. One with the line is done, as of that timestamp.
- A review's `## Disposition` section is the ground truth for what actually happened to each
  `CR-NNN` — not the transcript, which nobody re-reads.

## 3. Review filenames

Reviews save to `.superpowers/03-review/<YYYY-MM-DD-HHmm>-<slug>.md` — a 24-hour `HHmm`, not just
a date. Two reviews of the same branch on the same day (an initial pass and a follow-up after
fixes) get distinct filenames instead of the second overwriting the first.

## 4. How dispositions stay current

The `## Disposition` section is a current-state list, not a change log. When the user later says
"fix CR-003 now," `change-review` updates that row in place (`queued` → `fixed`) and refreshes the
`_Updated ..._` timestamp — it does not append a second `## Disposition` section or leave the
superseded row behind.

## 5. Syncing

Each note pushes to the sidecar immediately after it's written, using the same
`sidecar-sync.sh push` call the sidecar setup installs (see
[`docs/superpowers-sidecar.md`](superpowers-sidecar.md)). The sync is best-effort: if the script
is missing or fails, the skill reports it and continues rather than blocking on it.
