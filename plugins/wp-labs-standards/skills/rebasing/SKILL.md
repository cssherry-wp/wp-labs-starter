---
name: rebasing
description: Use when rebasing a branch, updating a branch onto a moved base, restacking onto a rebased or force-pushed parent branch in a stack of PRs, resolving rebase conflicts, or recovering from a rebase that went wrong — identifies commits by message and patch content rather than SHA (the parent branch may itself have been rebased) and requires a byte-identical verification before and after.
user-invocable: true
argument-hint: "[target-branch, e.g. origin/main or origin/feature/parent]"
allowed-tools: Bash
---

# Rebasing

A rebase rewrites history. The only way to know it did what you meant is to compare the patch
series before and after — never "it completed without conflicts, so it worked."

**Two rules drive everything below:**

1. **Identify commits by subject line and patch content, not SHA.** The upstream branch may have
   been rebased or squash-merged since you branched, so your commits can already exist upstream
   under different SHAs, and your recorded base SHA may no longer be an ancestor of anything.
2. **Verify byte-identical code before and after.** Every file you touched must have identical
   content after the rebase, except where the new base legitimately changed that file. Anything
   else is a silently dropped or mangled hunk.

## 1. Record the before-state

Do this **before** touching anything. Without it there is nothing to verify against.

```bash
OLDHEAD=$(git rev-parse HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git rev-parse --abbrev-ref '@{u}' 2>/dev/null || echo "no upstream set"
# The base your commits were actually written against:
OLDBASE=$(git merge-base "@{u}" HEAD 2>/dev/null || git merge-base origin/HEAD HEAD)
git fetch origin
NEWBASE=$(git rev-parse origin/main)   # or whatever the real target is
echo "OLDHEAD=$OLDHEAD OLDBASE=$OLDBASE NEWBASE=$NEWBASE"
```

Save the patch series and the cumulative diff:

```bash
git log --reverse --format='%H %s' "$OLDBASE..$OLDHEAD"     # your commits, in order
git diff "$OLDBASE" "$OLDHEAD" > /tmp/before.patch          # their net effect
git diff --name-only "$OLDBASE" "$OLDHEAD" > /tmp/before.files
```

`$OLDHEAD` is your safety net. `ORIG_HEAD` and `git reflog show "$BRANCH"` are the others — a
rebase never destroys the old commits, it only stops pointing at them.

## 2. Check whether the base was itself rebased

This is the case that makes SHA-based reasoning fail. Detect it before rebasing:

```bash
# Is the base your commits were written against still on the upstream branch?
git merge-base --is-ancestor "$OLDBASE" "$NEWBASE" && echo "base advanced normally" \
  || echo "BASE WAS REWRITTEN — $OLDBASE is not an ancestor of $NEWBASE"
```

If the base was rewritten, or if the branch has been open long enough that upstream may have
taken your work already, find out **by patch content**:

```bash
# '-' = this patch is already upstream (matched by patch-id), '+' = still yours to replay
git cherry -v "$NEWBASE" "$OLDHEAD"
```

`git cherry` compares `git patch-id` values, so it matches a commit that was cherry-picked,
rebased, or amended upstream even though its SHA and committer date changed. Cross-check by
subject line, because a squash-merge upstream changes the patch and defeats `patch-id`:

```bash
git log --format='%s' "$OLDBASE..$OLDHEAD" | while IFS= read -r s; do
  n=$(git log --oneline --fixed-strings --grep="$s" "$NEWBASE" | wc -l | tr -d ' ')
  [ "$n" -gt 0 ] && echo "ALREADY UPSTREAM (by subject): $s"
done
```

Commits reported as already upstream must **not** be replayed. Drop them explicitly (step 3)
rather than letting the rebase discover the duplicate and hand you a conflict against your own
code — that conflict is the single most common cause of a mangled rebase, because both sides look
plausible.

## 3. Rebase onto the explicit base

Always name both endpoints. A bare `git rebase origin/main` guesses the fork point from the
reflog, which is exactly what is unreliable after upstream rewrote history.

```bash
git rebase --onto "$NEWBASE" "$OLDBASE" "$BRANCH"
```

To drop commits that are already upstream, or to reorder, use the todo list — but note this
environment does not support interactive flags (`git rebase -i`). Do it non-interactively:

```bash
GIT_SEQUENCE_EDITOR="sed -i '' -e '/^pick <shortsha>/d'" \
  git rebase --onto "$NEWBASE" "$OLDBASE" "$BRANCH"
```

Turn on `git rerere` first if you expect to redo this rebase (a long-lived branch, or a retry
after a reset). It records how you resolved each conflict and replays it:

```bash
git config rerere.enabled true
```

### Restacking onto a rebased parent branch

The stacked case: your branch was cut from `feature/parent`, not from `main`, and the parent has
since been rebased or force-pushed. The mechanics are the same `--onto`, but `$OLDBASE` is now the
hard part — it must be the parent's **old** tip, the commit your branch was actually cut from, and
the parent ref no longer points there.

`git merge-base --fork-point` is the tool, because it consults the reflog of the ref you name, and
remote-tracking refs keep a reflog across fetches:

```bash
PARENT=feature/parent
git fetch origin
NEWBASE=$(git rev-parse "origin/$PARENT")
git reflog show "origin/$PARENT"                              # @{1} is the pre-force-push tip
OLDBASE=$(git merge-base --fork-point "origin/$PARENT" HEAD)  # reads that reflog
```

**Do not fall back to plain `git merge-base` here.** It returns the last common ancestor, which
after the parent was rewritten is a commit further back — below the parent's own work. Using it as
`$OLDBASE` makes the rebase replay the *parent's* commits along with yours, onto a parent that
already has them, and the conflict it raises is between the parent's old and new versions of its
own code. Verified on a scratch repo: `--fork-point` returned the correct old tip, while plain
`merge-base` returned an ancestor two commits lower and the rebase died with
`Could not apply 821065a... parent 2` — a commit that was never yours.

Sanity-check the boundary before rebasing. These must be only your commits:

```bash
git log --oneline --reverse "$OLDBASE..HEAD"
```

Then restack, and verify with step 5 as usual (`range-diff` should mark every commit `=`):

```bash
git rebase --onto "$NEWBASE" "$OLDBASE" "$BRANCH"
```

**If `--fork-point` returns nothing** (the reflog was pruned, or the branch was fetched into a
fresh clone that never saw the old tip), you have lost the boundary and must reconstruct it. Do
**not** reach for `git cherry "$NEWBASE" HEAD` and replay everything it marks `+`: it marks every
commit whose patch is not in the new parent, and a parent commit that was reworded or amended has
a different patch-id, so it appears in that list as though it were yours. In the same scratch repo
`git cherry` listed the parent's own `parent 2` as `+` alongside the two real child commits, and
cherry-picking that list conflicted immediately.

Reconstruct the boundary by inspection instead, then use it as `$OLDBASE`:

```bash
git log --oneline --format='%h %an %ad %s' --date=short "$NEWBASE..HEAD" | head -40
git log --author="$(git config user.email)" --oneline "$NEWBASE..HEAD"
```

Identify the oldest commit that is genuinely yours, and confirm the one below it belongs to the
parent, by subject and author. Authorship is a hint, not proof — on a shared parent branch you may
have written commits on both sides of the boundary.

For a stack more than two deep, restack bottom-up: each branch onto its parent's new tip, in
order, verifying each level before moving to the next. And on GitHub, a restacked child PR still
points at the old base branch — update it with `gh pr edit <n> --base <parent>` (or retarget to
`main` if the parent merged), or the PR diff will show the parent's commits as though they were
yours.

## 4. Resolve conflicts by intent, not by picking a side

At each conflict, the question is not "ours or theirs" — it is "what did this commit mean to do,
and what does the file now need to look like for that to still hold?"

```bash
git log -1 --format='%B' REBASE_HEAD    # the commit message: the author's stated intent
git show REBASE_HEAD -- <file>          # what this commit did to this file, in isolation
git diff                                # the conflicted state
```

Read the commit message first. It says what the change was for; the diff only says what it
touched. When the new base has refactored the code around your hunk, reapply the *intent* to the
new shape rather than restoring your old lines verbatim.

Never resolve by taking a whole side blind (`--ours`/`--theirs`) unless you have read both and
they are genuinely equivalent. Then:

```bash
git add <files> && git rebase --continue
```

If a commit's changes are now entirely present in the base, it becomes empty. That is expected
after step 2 found it upstream — `git rebase --skip` it, and say so in your report.

## 5. Verify byte-identical code (required)

A rebase is not done until this passes. `git range-diff` is the primary check: it pairs up old
and new commits and shows what changed in each patch.

```bash
git range-diff "$OLDBASE..$OLDHEAD" "$NEWBASE..$(git rev-parse HEAD)"
```

Every commit must be marked `=` (identical patch). A `!` means that patch changed during the
rebase — either a conflict resolution you made deliberately, or a hunk that got mangled. There is
no third possibility, so account for every `!` explicitly.

Then the file-content check, which is the one the two rules demand:

```bash
NEWHEAD=$(git rev-parse HEAD)
# Files YOU touched must be byte-identical, unless the base changed them too.
while IFS= read -r f; do
  if git diff --quiet "$OLDHEAD" "$NEWHEAD" -- "$f"; then
    echo "identical: $f"
  elif ! git diff --quiet "$OLDBASE" "$NEWBASE" -- "$f"; then
    echo "CHANGED, base also touched it (expected — review): $f"
  else
    echo "CHANGED, base did NOT touch it (BUG — the rebase altered your work): $f"
  fi
done < /tmp/before.files
```

Any line in the third category means the rebase silently changed code nobody asked it to. Stop
and investigate; do not push.

Finally confirm nothing outside your files drifted, and that the tests still pass:

```bash
git diff --stat "$OLDHEAD" "$NEWHEAD"    # should only show your files + base-driven changes
```

Run the project's test and lint commands. A rebase that compiles is not a rebase that works: your
hunk may have landed in a function the base renamed, and only the tests will say so.

## 6. Recovery

Nothing is lost until the reflog expires.

```bash
git rebase --abort                       # mid-rebase: back to the start, no damage
git reset --hard "$OLDHEAD"              # after a finished-but-wrong rebase
git reflog show "$BRANCH"                # if you did not record $OLDHEAD
```

## Pushing

A rebased branch needs a force-push, which can destroy a collaborator's work. Use the safe form,
which refuses if someone else pushed since you last fetched:

```bash
git push --force-with-lease
```

Never force-push a shared or default branch. On a branch with an open PR, force-pushing rewrites
what reviewers have already read: say so in the PR, and confirm with the user first if review
comments are anchored to lines you are about to move.

## Report

State: which commits were replayed, which were dropped as already-upstream (and how you
determined that — `patch-id` or subject), every `!` in the `range-diff` and why, and the result of
the byte-identical check. If any file landed in the "base did NOT touch it" category, lead with
that.
