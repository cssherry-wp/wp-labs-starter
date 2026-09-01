---
name: superpowers-sidecar-init
description: >-
  Adopt the current project into the global superpowers sidecar repo: migrate
  any existing .superpowers/ content — in the main repo and every one of its
  git worktrees — then replace each with a symlink into ~/.superpowers-sidecar
  so specs, plans, reviews, and sdd state sync across machines, worktrees, and
  CLAUDE_CONFIG_DIR profiles.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, AskUserQuestion
---

# /superpowers-sidecar-init

Adopts **this** project into the sidecar. Run it once per project, per
machine — it adopts the main repo and every one of its git worktrees in the
same pass, since each worktree has its own local `.superpowers/`.

Nothing else may invoke this skill — no hook, no other skill, no "this project
looks like it needs a sidecar" inference. Adoption creates directories in a
shared repo, so it happens only when the user asks for it by name.

## Prerequisites

The sidecar remote must already exist and be configured:

```bash
git config --global superpowers.sidecarUrl https://github.com/cssherry-wp/superpowers-sidecar
```

If `sidecarUrl` is unset, ask the user for the URL, run the command above with
their answer, and continue. Never create the remote for them.

## Steps

1. **Confirm the project key.**

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/skills/superpowers-sidecar-init/scripts/sidecar-init.sh" key
   ```

   Exit code 3 means the project has no `origin` remote: report that this
   project cannot be adopted (its `.superpowers/` stays local) and stop.

2. **List the worktree roots.**

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/skills/superpowers-sidecar-init/scripts/sidecar-init-all-worktrees.sh"
   ```

   One path per line: the main repo root plus every linked `git worktree`.
   `sidecar-init.sh` itself only ever acts on `$PWD`, so each root below is
   adopted by `cd`-ing into it first — same sidecar project folder, own local
   `.superpowers/`, own conflicts.

3. **Migrate each root.**

   ```bash
   (cd "$root" && bash "${CLAUDE_PLUGIN_ROOT}/skills/superpowers-sidecar-init/scripts/sidecar-init.sh" migrate)
   ```

   Run once per line from step 2. This creates the layout (once) and moves
   every non-colliding file for that root. Each line of output shaped
   `CONFLICT<TAB><path>` is a file that exists on both sides with different
   content — nothing was overwritten. Track which root each conflict came
   from; the same relative path can conflict independently in more than one
   worktree.

4. **Resolve conflicts, if any.** Do not resolve them one prompt at a time as
   they appear. Collect the full list first (across all roots), then for each
   conflicting path read both copies and present the choice with
   `AskUserQuestion`, batching up to 4 per call:

   - **Keep sidecar** — `rm` the local copy.
   - **Keep local** — `mv` the local copy over the sidecar copy.
   - **Keep both** — `mv` the local copy to `<name>-local.<ext>` in the sidecar.

   Summarize what differs (a short diff, or size and mtime) so the choice is
   informed. Re-run `migrate` (from that root) afterwards to sweep up
   anything that is now resolvable.

5. **Finalize each root.**

   ```bash
   (cd "$root" && bash "${CLAUDE_PLUGIN_ROOT}/skills/superpowers-sidecar-init/scripts/sidecar-init.sh" finalize)
   ```

   Run once per root from step 2, after every conflict for that root is
   resolved. Exit code 5 means files are still unresolved for that root —
   return to step 4. On success that root's `.superpowers` is a symlink, its
   `.gitignore` has a `.superpowers` line, and the sidecar has been committed
   and pushed.

6. **Report** the project key, which roots were adopted, what was migrated
   per root, how conflicts were resolved, and — if `finalize` warned that
   `sidecar-sync.sh` is not installed — tell the user to run
   `/setup-claude --sync` so the sync hooks start working.
