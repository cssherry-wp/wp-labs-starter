# Superpowers Sidecar

**Goal:** Keep a project's `.superpowers/` specs, plans, reviews, and sdd state synced across machines and `CLAUDE_CONFIG_DIR` profiles by storing them in a shared git repo instead of the project repo.

## 1. Set up the sidecar once per machine

Configure the sidecar remote (only needs doing once, globally):

```bash
git config --global superpowers.sidecarUrl https://github.com/cssherry-wp/superpowers-sidecar
```

Then install the sync hooks into `~/.claude/`:

```bash
/setup-claude --sync
```

If you run more than one `CLAUDE_CONFIG_DIR` profile (e.g. a separate config dir per client or environment), repeat the install for each one — the sync hooks live in that config dir's `settings.json`, not in the sidecar itself:

```bash
/setup-claude --sync --claude-dir /path/to/other/.claude
```

## 2. Adopt a project

Inside the project, run:

```
/superpowers-sidecar-init
```

This migrates any existing `.superpowers/` content into `~/.superpowers-sidecar/<org>/<repo>/`, then replaces the local `.superpowers/` with a symlink into that sidecar location.

Migration moves every file that doesn't already exist on the sidecar side. A file that exists on both sides with identical content is deduplicated silently. A file that exists on both sides with *different* content is reported as a conflict (`CONFLICT<TAB><path>`) and left untouched — nothing is ever overwritten automatically.

Conflicts are collected in full before any are resolved, then presented in batches (up to 4 at a time) with the choice: keep sidecar, keep local, or keep both (the local copy is renamed `<name>-local.<ext>`). After resolving, migration is re-run to sweep up anything now resolvable, then the project is finalized: the symlink is created, `.gitignore` gets a `.superpowers` line, and the sidecar is committed and pushed.

## 3. Resume on another machine

Clone the project as usual, then run `/superpowers-sidecar-init` again from inside it. Because the project's `origin` remote resolves to the same `<org>/<repo>` key, the sidecar clone is fetched (or reused if already present) and the symlink is pointed at the already-populated folder — there's nothing local to migrate, so this step is close to instant.

## 4. How syncing works

Three triggers keep the sidecar in sync without manual `git` commands:

- **`SessionStart`** — pulls (`git pull --rebase`) the sidecar clone at the start of every Claude Code session, so you start with the latest state from any machine.
- **Per-document pushes** — skills that write into `.superpowers/` (e.g. `superpowers-sidecar-init` on finalize) push immediately after writing, so changes land in the sidecar remote right away rather than waiting for session end.
- **`Stop`** — sweeps as insurance at the end of every session, pushing anything that wasn't already pushed by a per-document push.

Every push commits with the message format:

```
<org>/<repo>: <context> — <files> (<timestamp>)
```

for example `cssherry-wp/my-app: session-end sweep (2026-08-31 14:32)`.

Both hooks and the skill call the same `sidecar-sync.sh pull` / `sidecar-sync.sh push "<message>"` script, so the commit/push/retry logic exists in one place. In a project that isn't adopted (no `.superpowers` symlink), the script exits silently — the hooks are safe to run everywhere.

## 5. When something goes wrong

If a push fails and an automatic `pull --rebase` retry can't resolve it, you'll see:

```
WARNING: superpowers-sidecar push failed and rebase could not resolve it.
         Your work IS committed locally in ~/.superpowers-sidecar — resolve and push manually.
```

Nothing is lost: the commit already exists in `~/.superpowers-sidecar`. Resolve it like any other git conflict:

```bash
cd ~/.superpowers-sidecar
git status
# resolve conflicts, then:
git rebase --continue   # or: git rebase --abort and merge manually
git push
```
