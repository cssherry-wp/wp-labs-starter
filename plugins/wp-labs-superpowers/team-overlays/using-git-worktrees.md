<!-- wp-labs team overlay: BEGIN -->

## Team workflow: symlink the superpowers sidecar

If this project has already been adopted into the superpowers sidecar (its main working tree's
`.superpowers` is a symlink), a freshly created worktree needs its own symlink into that same
sidecar destination — otherwise `.superpowers` there is just an ordinary empty directory until
someone re-runs `/superpowers-sidecar-init` on it by hand.

Run this once, from inside the new worktree, right after Step 1 creates it (whichever of Step 0's
already-in-a-worktree path, Step 1a, or Step 1b got you there):

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sidecar-sync.sh" worktree-link || true
```

Best-effort: if `sidecar-sync.sh` isn't installed, or the project was never adopted, this is a
silent no-op — nothing to report, nothing to block on.

<!-- wp-labs team overlay: END -->
