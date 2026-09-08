<!-- wp-labs team overlay: BEGIN -->

## Team workflow: note completion in the plan

In the **Finish** section, after the final whole-branch review is clean, append one line to the
plan file this run executed:

```
Implemented: <YYYY-MM-DD HH:mm>
```

Do this **before** deleting the plan's `sdd/` workspace, and sync it to the sidecar (best-effort —
report and continue if the script is missing or fails), using the same one-or-two-sentence
completion summary you're about to give the user as the commit message:

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sidecar-sync.sh" push "<the summary you gave the user>"
```

The note goes in the plan document, which survives; the workspace does not. Write it only when
every task is complete and the final review is clean — a partially executed plan gets no note.

<!-- wp-labs team overlay: END -->
