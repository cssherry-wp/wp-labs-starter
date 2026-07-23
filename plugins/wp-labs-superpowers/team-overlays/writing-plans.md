<!-- wp-labs team overlay: BEGIN -->

## Team workflow: save the plan

Write the plan to the **repository ROOT's** `.superpowers/02-plans/` — the main working tree, not
the current directory or a worktree. Resolve the root explicitly and ensure the folder self-ignores
(add the `.gitignore` if it is missing, even when the folder already exists):

```bash
repo_top=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
mkdir -p "$repo_top/.superpowers/02-plans"
[ -f "$repo_top/.superpowers/02-plans/.gitignore" ] || printf '*\n' > "$repo_top/.superpowers/02-plans/.gitignore"
```

The `.superpowers/` directory is the durable record for specs and plans — no tracker sync required.

<!-- wp-labs team overlay: END -->
