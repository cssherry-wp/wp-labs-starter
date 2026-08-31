---
name: superpowers-sidecar-init
description: >-
  Adopt the current project into the global superpowers sidecar repo: migrate
  any existing .superpowers/ content, then replace the directory with a symlink
  into ~/.superpowers-sidecar so specs, plans, reviews, and sdd state sync
  across machines and CLAUDE_CONFIG_DIR profiles.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, AskUserQuestion
---

# /superpowers-sidecar-init

Adopts **this** project into the sidecar. Run it once per project, per machine.

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

2. **Migrate.**

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/skills/superpowers-sidecar-init/scripts/sidecar-init.sh" migrate
   ```

   This creates the layout and moves every non-colliding file. Each line of
   output shaped `CONFLICT<TAB><path>` is a file that exists on both sides with
   different content — nothing was overwritten.

3. **Resolve conflicts, if any.** Do not resolve them one prompt at a time as
   they appear. Collect the full list first, then for each conflicting path
   read both copies and present the choice with `AskUserQuestion`, batching up
   to 4 per call:

   - **Keep sidecar** — `rm` the local copy.
   - **Keep local** — `mv` the local copy over the sidecar copy.
   - **Keep both** — `mv` the local copy to `<name>-local.<ext>` in the sidecar.

   Summarize what differs (a short diff, or size and mtime) so the choice is
   informed. Re-run `migrate` afterwards to sweep up anything that is now
   resolvable.

4. **Finalize.**

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/skills/superpowers-sidecar-init/scripts/sidecar-init.sh" finalize
   ```

   Exit code 5 means files are still unresolved — return to step 3. On success
   `.superpowers` is a symlink, the project's `.gitignore` has a `.superpowers`
   line, and the sidecar has been committed and pushed.

5. **Report** the project key, what was migrated, how conflicts were resolved,
   and — if `finalize` warned that `sidecar-sync.sh` is not installed — tell the
   user to run `/setup-claude --sync` so the sync hooks start working.
