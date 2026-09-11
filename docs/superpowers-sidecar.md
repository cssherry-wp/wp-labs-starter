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
- **`Stop`** — two hooks run in sequence at the end of every session:
  - `plan-sync.sh` copies this session's Plan Mode plan into `.superpowers/02-plans/` under the team's dated-slug naming, if it isn't already there. Plan Mode (the `ExitPlanMode` flow) writes its plan to a global, per-user location (`~/.claude/plans/<slug>.md`) that isn't tied to any project, and unlike the `writing-plans` skill nothing else syncs that file into the project. The plan is located via the Stop hook's transcript, so other projects' plans in that shared directory aren't swept in.
  - `sidecar-sync.sh sweep` then runs as insurance, pushing anything that wasn't already pushed by a per-document push — including whatever `plan-sync.sh` just copied, since it runs first and lands the plan in the same push. `sweep` builds its own commit message, so the `<org>/<repo>` key is derived in one place rather than inline in the hook.

Every push commits with the message format:

```
<org>/<repo>: <context> — <files> (<timestamp>)
```

for example `cssherry-wp/my-app: session-end sweep (2026-08-31 14:32)`.

Both hooks and the skill call the same `sidecar-sync.sh pull` / `sidecar-sync.sh push "<message>"` / `sidecar-sync.sh sweep` script, so the commit/push/retry logic exists in one place. In a project that isn't adopted (no `.superpowers` symlink), the script exits silently — the hooks are safe to run everywhere.

The symlink lives in the **main** working tree, so the script resolves that root (via `git rev-parse --git-common-dir`) rather than `$PWD`. A session run from a `git worktree` therefore syncs normally.

## 5. Secrets are never pushed

`git add -A` would otherwise publish whatever is sitting in `.superpowers/`, and specs and plans routinely quote real tokens and connection strings while being drafted. Before committing, the script scans the newly staged lines for credential shapes — AWS access keys, private-key blocks, GitHub/Slack/OpenAI tokens, and `api_key`/`secret`/`password`/`token` assignments with a long value. On a hit it commits nothing, pushes nothing, and prints the offending `file: line`:

```
WARNING: superpowers-sidecar push BLOCKED — the staged changes look like they contain secrets:
         org/repo/01-specs/design.md: aws_secret_access_key = AKIA...
         Nothing was committed or pushed. Redact the values in ~/.superpowers-sidecar, then re-run.
```

Redact the value and the next sync goes through. For a false positive, override it for one command:

```bash
SIDECAR_ALLOW_SECRETS=1 bash ~/.claude/sidecar-sync.sh sweep
```

Only newly staged lines are scanned, deliberately: scanning all tracked content would let one already-committed false positive wedge every future push. This is a safety net against the obvious mistake, not a secrets scanner — keep the sidecar remote **private** regardless.

**Worktrees:** `sidecar-sync.sh` resolves the **main** working tree's root (via `git rev-parse --git-common-dir`) rather than `$PWD`, so `pull`, `push`, and `sweep` all work from a `git worktree` checkout the same as from the main tree — the `SessionStart` pull and `Stop` sweep are not no-ops there. A fresh worktree still has no `.superpowers` symlink of its own, though; skills that read or write `.superpowers/*` paths directly from `$PWD` (rather than going through `sidecar-sync.sh`) need one, so run `sidecar-sync.sh worktree-link` from inside the worktree to give it a symlink into the same sidecar destination plus the matching `.gitignore` line.

## 6. When something goes wrong

If a push fails and an automatic `pull --rebase` retry can't resolve it, you'll see:

```
ERROR: superpowers-sidecar push failed and rebase could not resolve it.
       Your work IS committed locally in ~/.superpowers-sidecar — resolve and push manually.
```

Every outcome is now reported: `OK:` on success (including `OK: nothing to sync`), `ERROR:` on a
real failure, with a non-zero exit. Silence means the script decided it had nothing to do — the
project isn't adopted (no `.superpowers` symlink), or `claude-lib.sh` is missing from your config
dir, which it sources and without which every sync is a silent no-op. Re-run
`/setup-claude --sync` to reinstall both files if syncing stops happening with no message at all.

Nothing is lost: the commit already exists in `~/.superpowers-sidecar`. Resolve it like any other git conflict:

```bash
cd ~/.superpowers-sidecar
git status
# resolve conflicts, then:
git rebase --continue   # or: git rebase --abort and merge manually
git push
```
