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
- **Reviews:** `<repo-top-level>/.superpowers/03-review/YYYY-MM-DD-HHmm-<slug>.md`

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
- **Do not create a `.gitignore` inside `.superpowers/` or any of its subfolders.** Creating the
  folder is enough:

  ```bash
  for d in 01-specs 02-plans 03-review; do
    mkdir -p "$repo_top/.superpowers/$d"
  done
  ```

  The old per-folder `.gitignore` containing `*` existed to hide these documents from the host
  repo. That job now belongs to a single `.superpowers` line in the project's own `.gitignore`,
  added when the project is adopted into the superpowers sidecar (`/superpowers-sidecar-init`).
  Inside the sidecar this content is *meant* to be tracked, so a self-ignoring marker there would
  silently defeat the sync. If you find a leftover `.gitignore` in one of these folders, delete it.
- **Specs and plans are git-ignored working copies — do NOT commit them.** The GitHub tracking
  issue (see the lifecycle below) is their durable record. This overrides any "commit the design
  document / plan to git" step in the brainstorming or writing-plans skills.

If you are following the superpowers brainstorming or writing-plans skills, substitute these
paths wherever they reference `docs/superpowers/specs/` or `docs/superpowers/plans/`.

## Lifecycle: spec → issue → plan-comment → feature docs → progress notes

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

5. **Progress notes — each document records its own lifecycle.** These are notes *in the file*,
   independent of the tracker sync in steps 1–3:
   - When a spec becomes a plan, the **spec** gets `Promoted to plan: <plan-path> (<YYYY-MM-DD HH:mm>)`.
   - When a plan's implementation completes, the **plan** gets `Implemented: <YYYY-MM-DD HH:mm>`.
   - When review findings are triaged or later fixed, the **review** gets a `## Disposition`
     section listing each `CR-NNN` and its current outcome.

   After writing any of these, sync the document to the sidecar (best-effort; report and continue
   if it fails):

   ```bash
   bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sidecar-sync.sh" push \
     "<org>/<repo>: <skill-name> — <file> ($(date '+%Y-%m-%d %H:%M'))"
   ```
