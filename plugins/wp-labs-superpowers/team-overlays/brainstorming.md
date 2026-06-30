<!-- wp-labs team overlay: BEGIN -->

## Team workflow: sync the approved spec to a GitHub issue

Write the spec to the **repository ROOT's** `.superpowers/01-specs/` — the main working tree, not
the current directory or a worktree. Resolve the root explicitly and ensure the folder self-ignores
(add the `.gitignore` if it is missing, even when the folder already exists):

```bash
repo_top=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
mkdir -p "$repo_top/.superpowers/01-specs"
[ -f "$repo_top/.superpowers/01-specs/.gitignore" ] || printf '*\n' > "$repo_top/.superpowers/01-specs/.gitignore"
```

After the user approves the written spec (the User Review Gate passes) and BEFORE invoking
writing-plans, link the spec to GitHub issue tracking:

1. **Identify the tracking issue.** The spec derives from an existing issue if the conversation
   or the spec text references one (e.g. `#42` or a GitHub issue URL).
2. **If an existing issue is identified:** append the spec to it as a comment —
   `gh issue comment <number> --body-file <spec-path>`.
3. **If none is identified:** ask the user `Create a GitHub tracking issue for this spec? (Y/n)`.
   On yes (the default), create it with the spec as the body —
   `gh issue create --title "<spec slug>" --body-file <spec-path>`. On no, skip and note that no
   issue is linked.
4. **Record the references** in the spec file: `Tracking issue: <issue-url>` (writing-plans reads
   this to comment the plan) and, when you posted the spec as a comment, `Spec sync: <comment-url>`.

**Keep it in sync.** If you later revise the spec (e.g. during the spec review loop), update its
GitHub counterpart in place — do NOT post a duplicate:
- spec created as the issue body → `gh issue edit <number> --body-file <spec-path>`;
- spec posted as a comment → edit it via the recorded `Spec sync:` URL:
  `gh api --method PATCH /repos/{owner}/{repo}/issues/comments/<comment-id> -F body=@<spec-path>`.

**Specs are git-ignored working copies — do NOT commit the spec file.** The GitHub issue is its
durable record. This overrides any "commit the design document to git" step earlier in this skill.

If `gh` is missing or unauthenticated, report it and continue — never block the workflow on it.

<!-- wp-labs team overlay: END -->
