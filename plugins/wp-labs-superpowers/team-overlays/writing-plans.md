<!-- wp-labs team overlay: BEGIN -->

## Team workflow: post the plan to the tracking issue

Write the plan to the **repository ROOT's** `.superpowers/02-plans/` — the main working tree, not
the current directory or a worktree. Resolve the root explicitly and ensure the folder self-ignores
(add the `.gitignore` if it is missing, even when the folder already exists):

```bash
repo_top=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
mkdir -p "$repo_top/.superpowers/02-plans"
[ -f "$repo_top/.superpowers/02-plans/.gitignore" ] || printf '*\n' > "$repo_top/.superpowers/02-plans/.gitignore"
```

The plan is a git-ignored working copy — do NOT commit it; the tracking issue is its durable record.

After the plan file is saved and self-reviewed, post it to the spec's tracking issue:

1. Read the `Tracking issue:` line from the spec this plan is based on.
2. If a tracking issue is present, post the plan as a comment —
   `gh issue comment <number> --body-file <plan-path>` — and record `Plan sync: <comment-url>` in
   the plan file.
3. If the spec has no tracking issue, skip with a one-line note.

**Keep it in sync.** If you later revise the plan (e.g. during plan self-review or fixes), edit the
same comment in place using the recorded `Plan sync:` URL — do NOT post a duplicate:
`gh api --method PATCH /repos/{owner}/{repo}/issues/comments/<comment-id> -F body=@<plan-path>`
(the `<comment-id>` is the trailing number in the comment URL).

If `gh` is missing or unauthenticated, report it and continue.

<!-- wp-labs team overlay: END -->
