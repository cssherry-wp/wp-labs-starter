---
name: codebase-audit
description: Audit an entire repository (not a diff) across three lenses — over-engineering, correctness, and security — producing a confidence-scored report in change-review's format, with file:line on every finding so a later fix pass can act. Report-only: never edits or commits. Fans out one agent per module/slice and synthesizes. Trigger when the user asks to audit the whole codebase, review the entire repo, find bloat/bugs/vulns across all code, or otherwise review the tree rather than a diff/PR.
user-invocable: true
allowed-tools: Read, Bash, Grep, Glob, Agent, Skill
argument-hint: "[path] [--effort low|medium|high|max]"
---

# Codebase audit

Whole-repo counterpart to `change-review`. Where `change-review` reviews a changeset, this audits
the entire tree across three lenses in one pass. **Report-only** — it never edits, fixes, or
commits. Every finding carries `file:line` so a later `/code-review --fix`, `change-review --fix`,
or manual pass can act on it.

Built-in `/code-review` and `/security-review` are change-scoped (they operate on the branch
diff), so this skill does NOT call them — it reuses their *lenses* and finding format, applied by
fan-out agents over slices of the repo.

## 0. Parse arguments

- Optional `path` — audit only that subtree (default: repo root).
- `--effort low|medium|high|max` — depth of each slice agent's review. Defaults to the reviewer's
  own default tier.

## 1. Scope the tree and estimate cost

List in-scope files with `git ls-files` (respects `.gitignore`); if a `path` is given, scope to
it. **Exclude mechanical/generated content**: lockfiles (`package-lock.json`, `yarn.lock`,
`poetry.lock`, `Cargo.lock`), build output (`dist/`, `build/`, `*.min.*`), vendored dirs
(`node_modules/`, `vendor/`), and generated files (snapshots, codegen, `*.generated.*`).

Count files and total lines in scope, then print an **approximate cost estimate** before the
fan-out, e.g.:

> Auditing 214 files (~38k lines) across ~12 slices → ~12 agents. Full-repo pass, may be
> token-intensive. Proceeding.

There is no size cap — full coverage — so the estimate is the guardrail. For a very large tree,
say so plainly so the user can interrupt.

## 2. Slice the tree

Group in-scope files into size-bounded slices, one per coherent module/directory:

- Keep a slice within ~15 files or ~2000 lines, whichever comes first.
- Don't split a small directory; split an oversized one by subdirectory or file.
- Keep files read together (a module and its tests) in the same slice.

## 3. Fan out — one agent per slice

Dispatch one Agent per slice (batch to a sane concurrency — don't launch hundreds at once). Give
each agent the slice's file list and instruct it to apply all three lenses in a single read and
return findings as JSON.

**Lens 1 — over-engineering** (ponytail lens): `delete:` dead code / speculative features;
`stdlib:` hand-rolled things the standard library ships; `native:` deps doing what the platform
already does; `yagni:` abstractions with one implementation / config nobody sets; `shrink:` same
logic in fewer lines. Name the replacement.

**Lens 2 — correctness** (`/code-review` lens): real defects with a concrete failure scenario
(null/undefined, off-by-one, wrong error handling, race, resource leak), plus reuse/efficiency
issues.

**Lens 3 — security** (vuln taxonomy): injection (SQL/command/template), SSRF, path traversal,
insecure deserialization, missing authn/authz, secrets in code, unsafe crypto. `/security-review`
is change-scoped, so this taxonomy is the lens.

Each finding: `{ file, line, category (over-engineering|correctness|security), severity
(high|med|low), confidence (0-100), summary, detail, suggestion }`.

## 4. Confidence scoring

Same scale as `change-review`:

- 0–49: uncertain / possible false positive — surface as a suggestion.
- 50–79: likely real but low-impact — suggestion.
- 80–100: verified, high-impact, or a clear vuln — a blocker.

Report all findings; do not drop by score.

## 5. Synthesize

Collect all slice findings. Dedup issues that span slice boundaries (same root cause reported
twice). Rank: security and correctness by severity × confidence; over-engineering biggest-cut
first. Produce the report below.

## 6. Output format

```
## Codebase audit — <path or repo>, <N> files / ~<L> lines, <S> slices

### Over-engineering
- <file:line> — <tag> <what to cut> → <replacement> (confidence N)   (or: Lean already)
_net: -<N> lines / -<M> deps possible_

### Correctness
- [HIGH/MED/LOW] <file:line> — <bug + failure scenario> → <fix> (confidence N)   (or: No obvious defects)

### Security
- [HIGH/MED/LOW] <file:line> — <vuln> → <remediation> (confidence N)   (or: No issues found)

### Verdict
**Must fix:**
- <high-severity, high-confidence, ordered>   (or: None)

**Worth doing:**
- <med/low items>   (or: None)

<one line: overall health + the single highest-value action>
```

Report-only. Do not edit, fix, or commit — the `file:line` anchors are the seam for a separate fix
pass.

## Notes

- See `../change-review/review-skills-map.md`: `codebase-audit` is the whole-repo sibling of
  `change-review`. `change-review` reviews a diff and dispatches the deep change-scoped passes;
  `codebase-audit` reviews the whole tree and reuses those passes' lenses via fan-out (it calls
  neither).
- Respect the repo's own stated rules (CLAUDE.md / AGENTS.md / CONTRIBUTING) over generic priors.
- For large trees, fan out with the Agent tool; the final report must still follow the structure
  above.
