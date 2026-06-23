# git-hooks/pre-commit

A **git hook** (not a Claude hook). Git runs it on every `git commit`.

**Install:** `make install-hooks` symlinks `.git/hooks/pre-commit` →
`.sdlc-hooks/pre-commit` (the skill copies this file there at scaffold time).

**Runs:** gitleaks secret scan (if installed) → `make check` → `make typecheck`.
A non-zero exit from gitleaks or `make check` aborts the commit.
