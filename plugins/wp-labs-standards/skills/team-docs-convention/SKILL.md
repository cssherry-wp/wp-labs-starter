---
name: team-docs-convention
description: Team convention for where specs and plans are saved. Use when brainstorming a spec, writing an implementation plan, or referencing spec/plan files — overrides any default doc path (including superpowers' docs/superpowers/... paths).
user-invocable: false
---

# Team Docs Convention

When creating or referencing design specs and implementation plans, use these paths and
naming — they **override** any default a skill suggests (e.g. superpowers' `docs/superpowers/specs/`
and `docs/superpowers/plans/`):

- **Specs:** `<repo-top-level>/.superpowers/01-specs/YYYY-MM-DD-HHmm-<name-of-spec>.md`
- **Plans:** `<repo-top-level>/.superpowers/02-plans/YYYY-MM-DD-HHmm-<name-of-plan>.md`

Rules:
- Use a 24-hour `HHmm` timestamp in the filename so multiple docs created the same day sort correctly.
- `<name-of-spec>` / `<name-of-plan>` is a short kebab-case slug.
- **Always the repository ROOT's `.superpowers/` — never the current working directory or a
  worktree subdirectory.** `<repo-top-level>` is the top-level directory of the main working tree.
  Resolve it explicitly (don't assume the cwd):
  ```bash
  repo_top=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
  ```
  From a normal checkout this is the repo root; from a git worktree it is the **main** working
  tree's root (not the worktree). Every worktree therefore shares one durable location, and the
  docs survive a worktree being removed.
- **Ensure each folder has a self-ignoring `.gitignore` — add it if it is missing**, whether the
  folder is brand new or already exists from a previous run. Same pattern superpowers uses for its
  `sdd/` scratch:
  ```bash
  for d in 01-specs 02-plans; do
    mkdir -p "$repo_top/.superpowers/$d"
    [ -f "$repo_top/.superpowers/$d/.gitignore" ] || printf '*\n' > "$repo_top/.superpowers/$d/.gitignore"
  done
  ```
  The `*` ignores everything in the folder, including the `.gitignore` itself, so nothing is
  tracked and the host repo's root `.gitignore` is left untouched. Run this check every time you
  write a spec or plan — it is a no-op once the `.gitignore` exists.
- **Specs and plans are git-ignored working copies — do NOT commit them.** The GitHub tracking
  issue (see the lifecycle below) is their durable record. This overrides any "commit the design
  document / plan to git" step in the brainstorming or writing-plans skills.

If you are following the superpowers brainstorming or writing-plans skills, substitute these
paths wherever they reference `docs/superpowers/specs/` or `docs/superpowers/plans/`.

## Lifecycle: spec → issue → plan-comment → feature docs

These steps apply whether you use stock superpowers or the team fork:

1. **Spec → issue** (after the spec is approved): if the spec derives from an existing GitHub
   issue, append it as a comment (`gh issue comment <n> --body-file <spec>`). Otherwise ask
   `Create a GitHub tracking issue for this spec? (Y/n)` and on yes create it
   (`gh issue create --title "<slug>" --body-file <spec>`). Record both references in the spec
   file (a working copy — not committed): `Tracking issue: <issue-url>` and, when you posted the
   spec as a comment, `Spec sync: <comment-url>`. The issue is the spec's durable record.
2. **Plan → comment** (after the plan is saved): read the spec's `Tracking issue:` line and post
   the plan as a comment (`gh issue comment <n> --body-file <plan>`). Record `Plan sync: <comment-url>`
   in the plan file. Skip if no issue is linked.
3. **Keep the issue in sync on every change.** Specs and plans are living documents — whenever you
   revise one *after* it has been synced, update its GitHub counterpart in place so the issue never
   goes stale (do not just post a new comment):
   - Spec that IS the issue body → `gh issue edit <n> --body-file <spec>`.
   - Spec or plan posted as a comment → edit that comment using the recorded `Spec sync:` /
     `Plan sync:` URL: `gh api --method PATCH /repos/{owner}/{repo}/issues/comments/<comment-id> -F body=@<file>`
     (the `<comment-id>` is the trailing number in the comment URL).
   This applies during the spec review loop, plan self-review, and any later edit.
4. **Implementation → docs** (after implementation completes): write a task-oriented
   usage/adaptation guide for the feature into `docs/<kebab-name>.md` — a how-to guide, not a
   dated changelog.

If `gh` is missing or unauthenticated, report and continue; never block on it.
