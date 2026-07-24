# Using Queue Groups

**Goal:** Organise `/queue` backlog items into named groups so you can triage, bulk-action, and filter by theme rather than item-by-item.

## When to use this

- You have several queued items that fall into distinct themes (e.g. `ci-fixes`, `docs`, `perf`) and want to act on a whole theme at once during drain.
- You want items pre-labelled at capture time so drain is faster.
- You are migrating items from another session and want to group them after import.

## 1. Capture an item with a group

Pass `--group <name>` anywhere before the ask text:

```
/queue --group ci-fixes Fix the flaky auth test
/queue --high --group docs Update the onboarding README
```

The group name is written into the queue file immediately. Order of flags before the ask does not matter.

## 2. What group-tagged items look like

Open `~/.claude/queue/<session-id>.md` — each tagged item contains a `group:` field:

```
- [ ] Fix the flaky auth test
  queued: 2026-07-24 10:00:00
  group: ci-fixes
  ctx: my-project
```

`q list <session-id>` shows `[group]` badges inline:

```
1. [ci-fixes] Fix the flaky auth test
   queued: 2026-07-24 10:00:00

2. [H] [docs] Update the onboarding README
   queued: 2026-07-24 10:00:00
```

## 3. Filter the list to a single group

```bash
~/.claude/queue/q list <session-id> --group ci-fixes
```

Only items whose `group:` field matches exactly are shown.

## 4. Assign or reassign a group manually

```bash
~/.claude/queue/q write-group <session-id> <n> "docs"
```

`<n>` is the 1-indexed open-item number. This is a no-op if the item already has a `group:` field.

## 5. How drain (Mode B) handles groups

During `/queue` drain, after writing interpretations, Claude:

1. Calls `q list` to find items without a `[group]` badge.
2. Infers a short group name for each ungrouped item from its ask and interpretation.
3. Writes the inferred group with `q write-group`.
4. Shows a confirmation table and applies any reassignments you reply with.

For **≤ 4 items**, the `AskUserQuestion` label for each item is prefixed `[group]` when a group is set.

For **> 4 items**, the triage table includes a `Group` column. You can reply with per-item dispositions or group-level bulk actions:

```
ci-fixes implement
docs queue
5 cancel
```

Group-level keywords:
- `<group> implement` — run all items in the group
- `<group> queue`     — keep all items, skip this drain
- `<group> filter`    — show only that group; re-ask for the rest after

## 6. Groups after migration (Mode D)

After `/queue migrate` imports items from another session, Claude runs the same grouping step on the newly-imported items — inferring groups and asking for confirmation before proceeding.

## Reference

| Command | What it does |
|---------|-------------|
| `q add <sid> --group <name> "<ask>"` | Capture with group |
| `q write-group <sid> <n> "<name>"` | Assign/overwrite group on item N |
| `q list <sid>` | List all open items; shows `[group]` badges |
| `q list <sid> --group <name>` | Filter to a single group |
