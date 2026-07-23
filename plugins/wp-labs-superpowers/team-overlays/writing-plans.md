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

The plan is a git-ignored working copy — do NOT commit it; the tracker issue is its durable record.

After the plan file is saved and self-reviewed, log it to the tracker:

1. Read the `Tracking issue:` line from the spec this plan is based on. A GitHub value is an issue
   number or URL; a Jira value is a key like `PROJ-123`.
2. **If a tracking issue is present,** post the plan as a comment on it:
   - GitHub: `gh issue comment <number> --body-file <plan-path>`
   - Jira: `acli jira workitem comment --key <KEY> --body-file <plan-path>`
   Record `Plan sync: <comment-ref>` in the plan file.
3. **If no tracking issue is present,** ask `Log this plan to a tracker? [github / jira / neither]`
   and create one with the plan as the body:
   - **github** → `gh issue create --title "<plan slug>" --body-file <plan-path>`.
   - **jira** → resolve the project key (`JIRA_PROJECT` env → repo-local `git config jira.project` →
     ask `Which Jira project key?` once and persist with `git config jira.project "<KEY>"`), then
     ```bash
     { printf '%s\n' "<plan slug>"; cat <plan-path>; } > "$repo_top/.superpowers/02-plans/.jira-workitem"
     acli jira workitem create --project "$JIRA_KEY" --type Task \
       --from-file "$repo_top/.superpowers/02-plans/.jira-workitem" --json
     ```
     (capture the key from `--json` output via `| jq -r .key`).
   - **neither** → skip with a one-line note.
   Record the new `Tracking issue: <url-or-key>` in the plan file.

**Keep it in sync.** If you later revise the plan (e.g. during plan self-review or fixes), edit the
same comment in place — do NOT post a duplicate:
- GitHub: `gh api --method PATCH /repos/{owner}/{repo}/issues/comments/<comment-id> -F body=@<plan-path>`
  (the `<comment-id>` is the trailing number in the recorded `Plan sync:` URL).
- Jira: re-run the comment command with `--edit-last`.

If the chosen CLI (`gh` or `acli`) is missing or unauthenticated, report it and continue.

<!-- wp-labs team overlay: END -->
