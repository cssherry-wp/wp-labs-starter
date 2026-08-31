<!-- wp-labs team overlay: BEGIN -->

## Team workflow: note completion in the plan

In **Step 3: Complete Development**, before handing off to
`superpowers:finishing-a-development-branch`, append one line to the plan file you just executed:

```
Implemented: <YYYY-MM-DD HH:mm>
```

Then sync it to the sidecar (best-effort — report and continue if the script is missing or fails):

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sidecar-sync.sh" push \
  "<org>/<repo>: executing-plans — implemented <plan-filename>.md ($(date '+%Y-%m-%d %H:%M'))"
```

Write the line only when every task in the plan is complete and its tests pass. A partially
executed plan gets no note — an `Implemented:` line that is not true is worse than no line, because
the next person to open the plan on another machine will trust it.

<!-- wp-labs team overlay: END -->
