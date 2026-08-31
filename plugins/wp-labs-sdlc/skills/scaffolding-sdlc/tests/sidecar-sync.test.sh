#!/usr/bin/env bash
# Unit tests for sidecar-sync.sh. Builds throwaway git repos in a temp dir.
# Requires: git. Run: bash tests/sidecar-sync.test.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../templates/claude/sidecar-sync.sh"
fail=0

check() {
  local name="$1" got="$2" want="$3"
  if [ "$got" = "$want" ]; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"; echo "  want: $want"; echo "  got:  $got"; fail=1
  fi
}

# Build a bare "remote", a sidecar clone, and a fake project.
setup() {
  TMP="$(mktemp -d)"
  git init -q --bare "$TMP/remote.git"
  git clone -q "$TMP/remote.git" "$TMP/sidecar"
  git -C "$TMP/sidecar" config user.email t@t.t
  git -C "$TMP/sidecar" config user.name t
  # Pin the branch name: the default varies by git version/config, and `git push`
  # with no upstream is exactly what the script under test relies on.
  git -C "$TMP/sidecar" checkout -q -b main
  mkdir -p "$TMP/sidecar/org/repo/01-specs"
  echo seed > "$TMP/sidecar/org/repo/01-specs/seed.md"
  git -C "$TMP/sidecar" add -A
  git -C "$TMP/sidecar" commit -qm seed
  git -C "$TMP/sidecar" push -q -u origin main
  # Ensure remote HEAD points to main (git version compatibility)
  git -C "$TMP/remote.git" symbolic-ref HEAD refs/heads/main
  mkdir -p "$TMP/project"
  ln -s "$TMP/sidecar/org/repo" "$TMP/project/.superpowers"
}
teardown() { rm -rf "$TMP"; }

# --- not adopted: both subcommands are silent no-ops ---
setup
mkdir -p "$TMP/plain"
out="$(cd "$TMP/plain" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "msg" 2>&1; echo "rc=$?")"
check "push no-ops when .superpowers is not a symlink" "$out" "rc=0"
out="$(cd "$TMP/plain" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" pull 2>&1; echo "rc=$?")"
check "pull no-ops when .superpowers is not a symlink" "$out" "rc=0"
teardown

# --- push commits and pushes a new file ---
setup
echo hello > "$TMP/project/.superpowers/01-specs/new.md"
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "org/repo: test — new.md (now)") >/dev/null 2>&1
check "push created a commit" \
  "$(git -C "$TMP/sidecar" log -1 --pretty=%s)" "org/repo: test — new.md (now)"
check "push reached the remote" \
  "$(git -C "$TMP/remote.git" log -1 --pretty=%s)" "org/repo: test — new.md (now)"
teardown

# --- push with nothing staged makes no commit ---
setup
before="$(git -C "$TMP/sidecar" rev-parse HEAD)"
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "should not commit") >/dev/null 2>&1
check "push is a no-op with no changes" "$(git -C "$TMP/sidecar" rev-parse HEAD)" "$before"
teardown

# --- push rebases and retries when the remote moved ahead ---
setup
git clone -q -b main "$TMP/remote.git" "$TMP/other"
git -C "$TMP/other" config user.email o@o.o
git -C "$TMP/other" config user.name o
echo other > "$TMP/other/org/repo/01-specs/other.md"
git -C "$TMP/other" add -A && git -C "$TMP/other" commit -qm "other side"
git -C "$TMP/other" push -q
echo mine > "$TMP/project/.superpowers/01-specs/mine.md"
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "mine") >/dev/null 2>&1
git -C "$TMP/remote.git" log --pretty=%s > "$TMP/subjects"
check "rebase-retry landed our commit" "$(grep -c '^mine$' "$TMP/subjects")" "1"
check "rebase-retry preserved theirs" "$(grep -c '^other side$' "$TMP/subjects")" "1"
teardown

# --- pull brings down remote commits ---
setup
git clone -q -b main "$TMP/remote.git" "$TMP/other"
git -C "$TMP/other" config user.email o@o.o
git -C "$TMP/other" config user.name o
echo remote > "$TMP/other/org/repo/01-specs/remote.md"
git -C "$TMP/other" add -A && git -C "$TMP/other" commit -qm "from remote"
git -C "$TMP/other" push -q
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" pull) >/dev/null 2>&1
check "pull fetched the remote commit" \
  "$([ -f "$TMP/sidecar/org/repo/01-specs/remote.md" ] && echo yes || echo no)" "yes"
teardown

# --- sweep derives the <org>/<repo> key itself ---
setup
echo hello > "$TMP/project/.superpowers/01-specs/swept.md"
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" sweep) >/dev/null 2>&1
check "sweep commits with the project key as prefix" \
  "$(git -C "$TMP/sidecar" log -1 --pretty=%s | sed 's/ (.*//')" \
  "org/repo: session-end sweep"
teardown

# --- a git worktree still syncs: the symlink lives in the MAIN working tree ---
# Regression guard. Resolving $PWD alone made every worktree session a silent
# no-op, which is where much of the work actually happens.
setup
git init -q "$TMP/project"
git -C "$TMP/project" config user.email p@p.p
git -C "$TMP/project" config user.name p
echo x > "$TMP/project/README.md"
git -C "$TMP/project" add README.md && git -C "$TMP/project" commit -qm init
git -C "$TMP/project" worktree add -q "$TMP/wt" -b feature
check "worktree has no .superpowers of its own" \
  "$([ -e "$TMP/wt/.superpowers" ] && echo yes || echo no)" "no"
echo from-worktree > "$TMP/project/.superpowers/01-specs/wt.md"
(cd "$TMP/wt" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "org/repo: from a worktree") >/dev/null 2>&1
check "push from a worktree reached the remote" \
  "$(git -C "$TMP/remote.git" log -1 --pretty=%s)" "org/repo: from a worktree"
teardown

# --- secrets block the push entirely ---
setup
printf 'aws_secret_access_key = AKIAIOSFODNN7EXAMPLE\n' \
  > "$TMP/project/.superpowers/01-specs/leak.md"
before="$(git -C "$TMP/sidecar" rev-parse HEAD)"
out="$(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "leaky" 2>&1)"
rc=$?
check "secret scan blocks the push" "$rc" "1"
check "secret scan made no commit" "$(git -C "$TMP/sidecar" rev-parse HEAD)" "$before"
check "secret scan warns on stderr" \
  "$(echo "$out" | grep -c 'push BLOCKED')" "1"
check "secret scan names the offending file" \
  "$(echo "$out" | grep -c '01-specs/leak.md')" "1"
check "secret scan leaves the file in place" \
  "$([ -f "$TMP/project/.superpowers/01-specs/leak.md" ] && echo yes || echo no)" "yes"
check "secret scan left nothing staged" \
  "$(git -C "$TMP/sidecar" diff --cached --name-only | wc -l | tr -d ' ')" "0"
teardown

# --- the override lets a false positive through ---
setup
printf 'token = %s\n' "notARealSecretButLooksLikeOne123" \
  > "$TMP/project/.superpowers/01-specs/maybe.md"
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" SIDECAR_ALLOW_SECRETS=1 \
  bash "$SCRIPT" push "org/repo: override") >/dev/null 2>&1
check "SIDECAR_ALLOW_SECRETS=1 pushes anyway" \
  "$(git -C "$TMP/remote.git" log -1 --pretty=%s)" "org/repo: override"
teardown

# --- ordinary prose is not mistaken for a secret ---
setup
cat > "$TMP/project/.superpowers/01-specs/prose.md" <<'PROSE'
# Design notes

The service reads its API key from the environment, never from this document.
Rotate the password quarterly. See the token exchange section below.
PROSE
(cd "$TMP/project" && SIDECAR_DIR="$TMP/sidecar" bash "$SCRIPT" push "org/repo: prose") >/dev/null 2>&1
check "prose mentioning secrets is not blocked" \
  "$(git -C "$TMP/remote.git" log -1 --pretty=%s)" "org/repo: prose"
teardown

exit "$fail"
