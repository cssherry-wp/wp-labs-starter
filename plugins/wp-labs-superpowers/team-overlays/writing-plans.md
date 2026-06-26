<!-- wp-labs team overlay: BEGIN -->

## Team workflow: post the plan to the tracking issue

Write the plan to the **top-level** repository's `.superpowers/02-plans/` (the main working tree,
not a worktree). When you first create that folder, drop a self-ignoring `.gitignore` into it so
the plan never reaches git:
`mkdir -p <top-level>/.superpowers/02-plans && printf '*\n' > <top-level>/.superpowers/02-plans/.gitignore`.
The plan is a git-ignored working copy — do NOT commit it; the tracking issue is its durable record.

After the plan file is saved and self-reviewed, post it to the spec's tracking issue:

1. Read the `Tracking issue:` line from the spec this plan is based on.
2. If a tracking issue is present, post the plan as a comment —
   `gh issue comment <number> --body-file <plan-path>`.
3. If the spec has no tracking issue, skip with a one-line note.

If `gh` is missing or unauthenticated, report it and continue.

<!-- wp-labs team overlay: END -->
