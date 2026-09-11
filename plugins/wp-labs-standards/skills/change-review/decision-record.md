# Decision record

The information a reader needs to decide whether to act on a review finding, beyond what the
finding is. Shared by `change-review` (diff reviews) and `codebase-audit` (whole-repo audits), and
rendered inline by the CI review job, so it is defined once here. A finding without this block
tells the reader something is wrong; the block tells them whether it is worth their time.

## Full record

Required on every architecture / security / structure finding and every correctness finding —
any severity, any confidence, including findings folded in from `/code-review`,
`/security-review`, and `/ponytail-review`. A LOW or low-confidence finding needs it as much as a
HIGH one: the reader still has to decide whether to spend time on it, and "low" is exactly where
the scenario and the cost of fixing decide the question.

```
- [ID] [SEV] <file:line> — <one-line defect> (confidence N)
  - **Scenario:** who or what is affected, and the user-visible or operational consequence.
    Plain terms, not the code path — "plans from another project get pushed to the shared
    remote", not "the loop does not filter $src".
  - **Trigger:** what must be true for this to fire, and how often that actually happens
    (every run / every session that does X / only with a crafted input). Severity without
    likelihood is not a decision.
  - **Evidence:** how you know — `reproduced` with the command and its output, or `inferred`
    from reading, and say which. Separate from confidence: a confidence-90 finding read off the
    page is weaker evidence than a confidence-70 one you reproduced. For an inferred finding,
    say what would confirm it.
  - **Origin:** `introduced here` or `pre-existing` (name the commit if you found it). Readers
    routinely and correctly decline pre-existing issues in an unrelated changeset.
  - **Proposed fix:** the change, plus its blast radius — files and call sites touched, and
    whether it changes a shared interface, a public API, or an on-disk/wire format.
  - **Alternatives:** each with pros and cons. **Always include doing nothing** as one option
    with its real cost, since that is the baseline the reader is choosing against. If there is
    genuinely only one sane fix, write "None — <why>" rather than inventing options.
  - **Cost & risk of fixing:** effort, what the fix itself could break (a tightened guard that
    now rejects valid input, a rename other code reads reflectively), and whether it needs a
    new or updated test to be safe.
  - **Caveats:** what this analysis assumes and did not verify — an environment you could not
    exercise, a caller you could not trace, a condition under which the recommendation flips.
    This is where the reader learns what your silence does not cover.
  - **Interacts with:** other finding IDs this subsumes, is blocked by, or is made moot by. A
    reader picking findings à la carte needs to know which ones do not compose.
  - **Recommendation:** one line, and say why. Vocabulary: `fix in this changeset` /
    `follow-up` / `accept` for a diff review; `fix now` / `schedule` / `accept` for an audit.
```

### Rules

- Keep each field to a line or two. Omit a field that genuinely does not apply rather than padding
  it — but `Scenario`, `Trigger`, `Evidence`, `Origin`, and `Recommendation` always apply.
- Do not skip the block because the finding might not be real. That is the reader's call, and the
  block — `Evidence` in particular — is how they make it.
- If the block grows past ~12 lines, the finding is probably two findings.
- `Caveats` and `Interacts with` are the two most often legitimately omitted. Omitting `Caveats`
  is a claim that you verified everything the finding rests on; make it deliberately.

## Light record

For findings that are cheaper decisions but still decisions — outlying changes, documentation
freshness, test coverage. Three items on one line under the headline:

```
  - **Origin:** … · **Cost:** … · **Recommendation:** …
```

`Cost` is effort plus whether the fix needs a test or a doc change. For outlying changes the
recommendation vocabulary is `keep` / `split into its own changeset` / `revert`, since the question
is where the change belongs, not whether it is correct.

Lint/style findings carry neither record: the tool's output is the evidence and the tool's fix is
the fix.

## Audit mode (whole repo, no diff)

Two fields read differently when there is no changeset:

- **Origin** cannot mean "introduced by this diff". Use `git blame` / `git log -S` to give the
  introducing commit and its age (`3 months`, `since initial import`). Age is decision-relevant on
  its own: a bug that has sat untriggered for two years has a different `Trigger` story than one
  landed last week, and the reader may want to know whether the author is still around.
- **Trigger** should say whether the code path is reachable at all. A whole-repo audit finds dead
  and near-dead code a diff review never sees, and "unreachable in practice" is a legitimate reason
  to `accept`.

Over-engineering findings keep a one-line form in audits: the scenario of dead flexibility is the
same every time (nobody uses it), the evidence is the grep that found no callers, and the cost of
removal is the net-lines figure. Add a record to one only when the deletion has a non-obvious risk
(a public API, a reflective lookup, a serialized shape).

## Auto-fix eligibility

A finding may be applied automatically (`--fix`, or the CI autofix commit) only when **all** hold:

1. confidence ≥ 80;
2. `Evidence` is `reproduced` — or the fix is one a tool verifies for you (a formatter, a linter's
   own `--fix`);
3. `Recommendation` is `fix in this changeset` (or `fix now` in an audit);
4. the fix is mechanical — one obvious edit, no judgment between approaches.

Confidence alone was the old gate. It let a confidently-inferred finding self-apply, which is the
false confidence the record exists to remove. Everything that fails any condition is reported as a
suggestion, never applied.

## Machine form

In `change-review-findings.json` the fields are `scenario`, `trigger`, `evidence`, `origin`,
`alternatives` (array), `fix_risk` (the Cost & risk line), `caveats`, `interacts_with` (array),
`recommendation` — one string each unless noted. The light record uses `origin`, `fix_risk`, and
`recommendation`. The CI renderer prints whichever are present, in the order above, as a labelled
list under the finding's detail; empty arrays print nothing.

## Handing a finding on

When a finding is deferred — queued with `/queue`, or logged as a tracker issue — the person who
picks it up later must have the same material the reviewer had. Carry the **whole record** into the
queue item or issue body, not the headline alone, in this shape:

```
<one-line defect>  (<file:line>, severity <sev>, confidence <N>)

Scenario: …
Trigger: …
Evidence: …
Origin: …
Proposed fix: …
Alternatives: …
Cost & risk of fixing: …
Caveats: …
Recommendation at review time: …
Reviewer's note: <any free text the user attached when deferring>

From: <review file path or PR URL>, finding <ID>
```

A headline-only issue read three months later has less to decide with than the reviewer did on the
day; that is how deferred findings turn into permanent ones.
