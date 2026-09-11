# shellcheck shell=bash
# Shared helpers for the hook scripts installed into ~/.claude. Both
# sidecar-sync.sh and plan-sync.sh are invoked by absolute path from
# settings.json, so this lib has to be installed alongside them in the
# config dir too, rather than living only in the plugin cache. Sourced only,
# never executed: no shebang logic, no `set -e`, safe under `set -uo pipefail`.

# Resolve the MAIN working tree root, worktree-safe (CLAUDE.md's prescribed
# approach). No $PWD fallback: callers must treat failure as "not in a
# project" and fail safe, not guess the cwd.
project_root() {
  local gcd
  gcd="$(git rev-parse --git-common-dir 2>/dev/null)" || return 1
  (cd "$gcd/.." 2>/dev/null && pwd -P)
}
