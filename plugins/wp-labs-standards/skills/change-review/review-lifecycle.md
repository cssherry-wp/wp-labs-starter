# Review lifecycle: persist, triage, disposition

What happens to a `change-review` report after it is printed. The review *method* lives in
`SKILL.md`; this file is the procedure around it, so the method stays readable. Everything here is
skipped under `--ci`, where `change-review-findings.json` is the deliverable and a privileged job
owns the side effects.

## 1. Persist the report

Save the prose report to `<repo-root>/.superpowers/03-review/<YYYY-MM-DD-HHmm>-<slug>.md`, where
`slug` is `uncommitted`, `pr-<N>`, or derived from the branch name. The `HHmm` is a 24-hour
timestamp — without it a second review of the same branch on the same day silently overwrites the
first.

`<repo-root>` is the **main** working tree's root, resolved the way `team-docs-convention`
prescribes (it owns the snippet; it resolves correctly from inside a throwaway worktree too).
Create the directory if absent:

```bash
repo_top=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
mkdir -p "$repo_top/.superpowers/03-review"
```

Do **not** add a self-ignoring `.gitignore` to this folder. In a project adopted into the
superpowers sidecar, `.superpowers` is a symlink and the project's own `.gitignore` already hides
it by name; inside the sidecar the reviews are meant to be tracked. In a project that has not been
adopted, the folder is untracked working scratch either way.

Then sync it to the sidecar (best-effort — report and continue on failure):

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sidecar-sync.sh" push \
  "<org>/<repo>: change-review — <YYYY-MM-DD-HHmm>-<slug>.md ($(date '+%Y-%m-%d %H:%M'))"
```

## 2. Interactive triage

Collect every **unfixed** finding from sections 2–7 by its `CR-NNN` ID.

**Check what is available first.** Deferring to `/queue` needs the `wp-labs-sdlc` plugin
(`wp-labs-sdlc:queue` in the available-skills list). If it is absent, say so once — one line, not a
lecture — and run triage without the queue option: every deferral becomes a tracker issue, which
carries the same handing-on body, so nothing is lost but the session-local backlog.

**≤ 4 unfixed findings**: `AskUserQuestion`, one question per finding, all in a single call.

- `header`: `"CR-NNN"` (+ section label if helpful, e.g. `"CR-007 Tests"`, max 12 chars).
- `question`: the finding's impact (what breaks or degrades if left as-is) and the trade-off of
  each choice, so the user can decide without re-reading the report. The decision record already
  holds this — draw from it rather than rewriting it.
- `options`, in this order (the tool rejects fewer than 2 — never go below that):
  1. label `"Fix it"`, description `"Apply the change now"`
  2. label `"Add to queue"`, description `"Defer to /queue for a later session"` — **omit this
     option when `/queue` is unavailable**
  3. label `"Log as issue"`, description `"Create a tracker issue and link it"`
  4. label `"Ignore"`, description `"Drop it"`

**> 4 unfixed findings**: render a markdown table, then prompt for dispositions as text:

| ID | Section | Finding | Sev | Confidence | Recommendation |
|----|---------|---------|-----|-----------|----------------|
| CR-001 | Correctness | `foo.ts:42` unused import | low | 85 | fix now |
| CR-003 | Security | `sync.ts:88` untrusted path copied to shared remote | high | 85 | fix now |
| CR-007 | Docs | `README.md` stale env-var table (pre-existing) | low | 70 | follow-up |
| … | … | … | … | … | … |

Carry `Recommendation` straight from each finding's decision record, and mark a `pre-existing`
origin inline as above — those two columns are what let a reader triage the table without
scrolling back to the findings.

Then ask: "For each finding reply: `<CR-NNN> fix|queue|issue|ignore [note]`. E.g.
`CR-001 fix CR-003 queue CR-005 ignore`." (Drop `queue` from the vocabulary when unavailable; if
the user types it anyway, treat it as `issue` and say so.)

The user may attach a free-text note to any choice; read it from `annotations[].notes` (≤ 4 path)
or inline in the reply (> 4 path) and carry it into the action.

### Acting on each selection

- **Fix it**: these are the findings the `--fix` pass left as suggestions — lower-confidence, or
  needing the judgment the user just supplied. Use the same group-then-dispatch approach as
  `SKILL.md` §6: group the selected findings by what fixing them takes, pick a model per group by
  the fix's difficulty (not this session's own model), one `Agent` call per group. A single
  selection can be applied directly.
- **Add to queue**: call `/queue` with the finding's **whole decision record** in the handing-on
  shape from `decision-record.md` — not the headline alone. `/queue` takes multi-line input: the
  first line becomes the item, the rest sub-bullets, which is what the shape is built for.
- **Log as issue**: `gh issue create` (or Jira via `acli`) with the same handing-on body, plus the
  user's note and a link back to the review file or PR; record the issue number.
- **Ignore**: record it as acknowledged.

Report one line: what was fixed, queued, logged, ignored.

## 3. Disposition

The spoken summary disappears with the conversation; the persisted file is what someone reads
later — on another machine too, since the sidecar syncs it. Append (or update, if present) a
`## Disposition` section at the end of the review document:

```markdown
## Disposition

_Updated 2026-08-31 14:22_

- CR-001: fixed · recommended fix in this changeset
- CR-003: queued · recommended fix in this changeset — revisit after the perf work lands
- CR-005: ignored · recommended follow-up — intentional, mirrors the upstream behaviour
- CR-007: logged #142 · recommended follow-up
```

Rules:

- One line per finding, by `CR-NNN`. Every finding gets a line — including those auto-fixed under
  `--fix`, which are `fixed`.
- Every line carries the review's **recommendation** next to the **decision**, always, even when
  they agree. Where they differ, the user's reason (their note) follows the dash. The file is then
  calibration data: over time it shows where reviewer and reader disagreed and, once the code has
  run, who was right.
- Carry across any free-text note the user attached.
- **Update in place after every later fix round.** "Fix CR-003 now" changes that row from `queued`
  to `fixed` and refreshes `_Updated …_`. Current state, not a change log: no second Disposition
  section, no superseded rows kept.
- Sync after every write, the same way the report was synced:

  ```bash
  bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sidecar-sync.sh" push \
    "<org>/<repo>: change-review — disposition for <slug> ($(date '+%Y-%m-%d %H:%M'))"
  ```

If the review file for the findings under discussion cannot be located (the findings came from a
session whose file was never persisted), say so and skip — do not invent a review file just to
hold a Disposition section.
