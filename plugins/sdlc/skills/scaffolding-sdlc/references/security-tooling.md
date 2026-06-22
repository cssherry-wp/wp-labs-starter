# Security tooling reference

The skill wires five complementary security layers. Enable per repo; the
playbook asks the user to confirm.

| Layer | Tool | Catches | Where | Secret needed |
|-------|------|---------|-------|---------------|
| Secrets | gitleaks | committed credentials | pre-commit + `security.yml` | none (uses GITHUB_TOKEN) |
| Dependencies (CVEs) | npm audit / pip-audit | known-vulnerable deps | `security.yml` | none |
| Dependency updates | Dependabot | outdated deps (auto-PRs) | `dependabot.yml` | none |
| SAST (patterns) | Semgrep | insecure code patterns | `security.yml` | `SEMGREP_APP_TOKEN` (optional) |
| SAST (semantic) | Claude `/security-review` | logic/semantic security issues | `code-review.yml` | `CLAUDE_CODE_OAUTH_TOKEN` |

## Notes
- **gitleaks** must be installed locally for the pre-commit scan
  (`brew install gitleaks`); the CI job needs no install.
- **Semgrep** runs `semgrep ci`; without `SEMGREP_APP_TOKEN` it uses the open
  rulesets. The gate tolerates findings (`|| true`) — tighten per repo.
- **Claude `/security-review`** is semantic and complements the deterministic
  scanners; it skips `[autofix]` commits to avoid re-reviewing auto-fixes.
- **CodeQL** is intentionally excluded. To add it later, create a separate
  `codeql.yml`; it does not replace any layer above.
