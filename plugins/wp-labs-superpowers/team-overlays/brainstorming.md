<!-- wp-labs team overlay: BEGIN -->

## Team workflow: sync the approved spec to an issue tracker

Write the spec to the **repository ROOT's** `.superpowers/01-specs/` — the main working tree, not
the current directory or a worktree. Resolve the root explicitly and ensure the folder self-ignores
(add the `.gitignore` if it is missing, even when the folder already exists):

```bash
repo_top=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
mkdir -p "$repo_top/.superpowers/01-specs"
[ -f "$repo_top/.superpowers/01-specs/.gitignore" ] || printf '*\n' > "$repo_top/.superpowers/01-specs/.gitignore"
```

After the user approves the written spec (the User Review Gate passes) and BEFORE invoking
writing-plans, log the spec to an issue tracker.

1. **Identify an existing tracking issue.** The spec derives from one if the conversation or spec
   text references it — a GitHub issue (`#42` or its URL) or a Jira key (e.g. `PROJ-123`). If found,
   use that tracker and skip the prompt in step 2.
2. **If none is identified, ask:** `Log this spec to a tracker? [github / jira / neither]`.
   - **github** — create the issue with the spec as the body:
     `gh issue create --title "<spec slug>" --body-file <spec-path>`. Capture the printed URL.
   - **jira** — resolve the project key (see "Jira project resolution"), then create a work item
     whose summary is the spec slug and description is the spec body. acli's `--from-file` reads the
     summary from the file's first line and the description from the rest, so prepend the slug:
     ```bash
     { printf '%s\n' "<spec slug>"; cat <spec-path>; } > "$repo_top/.superpowers/01-specs/.jira-workitem"
     acli jira workitem create --project "$JIRA_KEY" --type Task \
       --from-file "$repo_top/.superpowers/01-specs/.jira-workitem" --json
     ```
     Capture the created key from the `--json` output (`| jq -r .key`).
   - **neither** — skip; note that no tracker issue is linked. The spec stays local-only.
3. **If an existing issue was identified in step 1,** append the spec as a comment instead of creating:
   - GitHub: `gh issue comment <number> --body-file <spec-path>`
   - Jira: `acli jira workitem comment --key <KEY> --body-file <spec-path>`
4. **Record the references** in the spec file: `Tracking issue: <url-or-key>` (writing-plans reads
   this to comment the plan) and, when you posted the spec as a comment, `Spec sync: <comment-ref>`.

**Jira project resolution.** Determine `JIRA_KEY` in this order: the `JIRA_PROJECT` env var; else the
repo-local `git config jira.project`; else ask `Which Jira project key?` once and persist it for this
repo with `git config jira.project "<KEY>"` so later runs don't ask again.

**Keep it in sync.** If you later revise the spec (e.g. during the spec review loop), update its
tracker counterpart in place — do NOT post a duplicate:
- GitHub issue body → `gh issue edit <number> --body-file <spec-path>`; comment → edit via the
  recorded `Spec sync:` URL:
  `gh api --method PATCH /repos/{owner}/{repo}/issues/comments/<comment-id> -F body=@<spec-path>`.
- Jira issue body → `acli jira workitem edit --key <KEY> --summary "<spec slug>" --description-file <spec-path>`;
  comment → re-run the comment command with `--edit-last`.

**Specs are git-ignored working copies — do NOT commit the spec file.** The tracker issue is its
durable record. This overrides any "commit the design document to git" step earlier in this skill.

If the chosen CLI (`gh` or `acli`) is missing or unauthenticated, report it and continue — never
block the workflow on it.

<!-- wp-labs team overlay: END -->
