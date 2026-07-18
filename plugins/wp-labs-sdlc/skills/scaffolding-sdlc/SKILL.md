---
name: scaffolding-sdlc
description: Use when starting a new repo or adding SDLC automation to an existing one — sets up lint, unit tests, Playwright e2e, security scanning, Dependabot, PR-status labels, pre-commit hooks, and Claude PR automation that run on every PR. Pass --setup-claude to instead configure the global ~/.claude/ environment (settings, plugins, CLAUDE.md, rules) on a fresh machine or new Claude Code install.
---

# Scaffolding SDLC

## Overview

Two modes:

- **Repo mode** (default): interactively bootstrap standardized SDLC automation
  into a repo — runnable starter app, Makefile, pre-commit hook, GitHub Actions
  CI/security/Claude-PR-automation, Dependabot, PR-status labels, and optional
  hosting (Docker + Azure Bicep).
- **`--setup-claude`**: configure the global `~/.claude/` environment on a fresh
  machine or new Claude Code install — settings.json with all recommended plugins
  and marketplaces, CLAUDE.md, and glob-scoped rules/. Use this before the first
  repo scaffold, or to onboard a new machine.

**Core principle (repo mode):** local == CI (both call the same Makefile
targets), and never clobber existing files — detect, diff, ask, merge. On an
existing repo, audit the full inventory and add only the missing pieces.

## When to use

- `--setup-claude`: fresh machine, new Claude Code install, or syncing global
  Claude config to the team standard.
- Starting a fresh repo that needs CI/quality gates.
- An existing repo with no `.github/workflows/`, no pre-commit checks, or
  inconsistent tooling.

## Prerequisites (tell the user up front)

- Authenticated `gh` CLI with repo admin (labels, branch protection).
- Repo secrets to add manually: `CLAUDE_CODE_OAUTH_TOKEN` (required for the four
  Claude workflows), `SEMGREP_APP_TOKEN` (optional).
- For `pr-rebase.yml` to re-trigger CI on rebased commits, add **either** a
  GitHub App (preferred) — secrets `REBASE_APP_ID` + `REBASE_APP_PRIVATE_KEY`,
  App permissions Contents: write and Pull requests: write, installed on the
  repo — **or** a fine-grained PAT `REBASE_TOKEN` (same two permissions) as a
  fallback. Without either it falls back to `GITHUB_TOKEN`, which still rebases
  but does not re-run CI.
- `gitleaks` installed locally for the pre-commit secret scan
  (`brew install gitleaks`).

## --setup-claude: Global Claude Setup

When the user passes `--setup-claude` (or says "setup claude", "set up my claude
environment", "configure claude globally"), run this workflow instead of the repo
scaffold below.

**What it configures** (all under `~/.claude/`, never inside any repo):

1. **settings.json** — deep-merge `templates/claude/settings.json` into
   `~/.claude/settings.json`. Team values win on conflict for scalar and object
   keys; existing personal keys not in the template are preserved. **Array values
   (e.g. `hooks.Stop`) are concatenated** so existing hooks survive. Show the diff
   before applying; ask before overwriting.

   Note: `enabledPlugins` entries that the template sets to `false` (e.g.
   `superpowers@claude-plugins-official`) will override a user's `true` — the
   template prefers `wp-labs-superpowers@wp-labs-starter` instead. The diff step
   makes this visible before it applies.

   ```bash
   merged=$(jq -s '.[0] * .[1] | .hooks.Stop = ((.[0].hooks.Stop // []) + (.[1].hooks.Stop // []))' \
     ~/.claude/settings.json templates/claude/settings.json)
   echo "$merged" > ~/.claude/settings.json
   ```

   This registers the wp-labs-starter, ponytail, and playwright-skill marketplaces
   and enables all recommended plugins. Claude Code auto-installs any plugin in
   `enabledPlugins` that is not yet cached on next launch — no manual `claude plugins
   install` needed.

2. **CLAUDE.md** — copy `templates/claude/CLAUDE.md` to `~/.claude/CLAUDE.md`. If
   it already exists, show the diff and ask before overwriting.

3. **rules/** — copy each file in `templates/claude/rules/` to `~/.claude/rules/`,
   skipping files that are already identical. For any file that differs, show the
   diff and ask.

   Included rules: `coding-guidelines.md` (always-apply), `python.md`,
   `js-ts.md`, `css.md`, `sql.md`, `context7.md`.

**Standalone (no Claude needed):** the user can also run
`scripts/setup-claude.sh` directly from a terminal — useful for bootstrapping a
fresh machine before Claude Code is configured. It is interactive and follows the
same detect/diff/ask/apply pattern.

```bash
bash plugins/wp-labs-sdlc/skills/scaffolding-sdlc/scripts/setup-claude.sh
```

After applying, tell the user to restart Claude Code so it picks up the new
settings and triggers plugin auto-install.

## Workflow (Repo Mode)

Run these steps in order. The template root is this skill's `templates/`
directory; copy from there.

1. **Detect & audit.** Run `scripts/detect-stack.sh` in the target repo and note
   its conventions: package manager (pip vs uv), config-file style (standalone
   `ruff.toml`/`pytest.ini` vs `[tool.*]`), project subdirectory (manifests under
   `app/`, `app/frontend/`, etc.), and existing frontend linter.

   Then produce a **scaffold inventory** — go through EVERY component this skill
   can add and mark each present / partial / missing:
   - dev-loop: `Makefile`, tool configs, `.gitignore`, manifest
   - starter app (greenfield only)
   - `git-hooks/pre-commit`
   - each workflow: `ci.yml`, `security.yml`, `code-review.yml` (two jobs — a
     read-only `review` job runs `change-review` and a privileged `apply` job
     applies its patch + posts findings), `claude.yml`,
     `claude-comment-triage.yml`, `pr-status-labels.yml`, `pr-rebase.yml`
   - branch protection on the default branch (require a PR to merge; block
     force-push and deletion) — see "Set branch protection" below
   - `dependabot.yml`; the managed labels; hosting (`Dockerfile`,
     `docker-compose.yml`, `infra/` Bicep, `azure-deploy.yml`)
   - Claude team settings (`.claude/settings.json`, `.claude/CLAUDE.md`,
     `.claude/rules/`: marketplaces, plugins, Stop hook, prose style rules,
     and glob-scoped coding guidelines)

   Present the inventory to the user. **On an existing repo, add only the
   missing pieces** and **explicitly ask about each gap** before adding it —
   don't assume. **Never overwrite existing files silently:** for anything that
   already exists, show the diff and ask. **Adapt, don't impose:** where the repo
   already has a convention, conform to it (e.g. add `pip-audit` for a pip repo,
   wire CI `working-directory` to the project subdir, call the repo's existing
   `make` targets) instead of forcing the template's defaults.

2. **Choose stack & scanners.** Present the detected stack and the menu —
   **TypeScript**, **Python**, or **Fullstack (Python + React)** — with brief
   pros/cons. **Pause and let the user customize** the choice; do not force a
   single option. For the Fullstack/React path, ask whether to scaffold the
   **minimal React harness** (default) or the **full structured_data stack**
   (Radix + Tailwind + lucide + react-router) — see
   `templates/fullstack/frontend/README.md`. Confirm which security scanners to
   enable (gitleaks default-on; dependency audit, Dependabot, Semgrep opt-in) —
   see `references/security-tooling.md`.

   **CSS/SCSS/Sass is its own independent language option** — it is not implied
   by TypeScript/Fullstack. A project can have stylesheets without a JS build
   (e.g. WordPress themes, PHP+CSS). Ask explicitly whether the project uses
   CSS/SCSS/Sass; if yes, it gets its own `styles` paths-filter and `stylelint`
   CI job regardless of the other language choices.

   **Language choice drives two downstream decisions** — record it explicitly
   before proceeding:
   - **CI jobs and path filters** (step 5): only include CI jobs for the chosen
     languages; path filters must match where those languages' files actually live
     in the project (detected in step 1).
   - **Claude rules** (step 8c): only copy language-relevant rules.

3. **Local dev loop.** Copy tool configs from the chosen stack's templates
   (`templates/<stack>/`). Only copy the `Makefile` if the stack includes
   TypeScript or Python — a CSS-only project has no build toolchain to
   orchestrate. Only merge `pyproject-tooling.toml` for Python stacks; only
   merge `package-scripts.json` for TypeScript stacks. Do not overwrite existing
   manifests — merge only. Create README and the manifest only if missing.

   **Assemble `.gitignore` from language snippets** in `templates/gitignore.d/`:
   always start with `common`, then append one snippet per chosen language:

   | Language | Snippet |
   |----------|---------|
   | Always | `common` |
   | Python | `python` |
   | TypeScript / JavaScript | `node` |
   | CSS / SCSS / Sass | `css` |

   Concatenate the relevant files in that order and write to `.gitignore`. If
   `.gitignore` already exists, merge (append any lines not already present) rather
   than overwriting. Adapt paths in the `node` snippet to match the project
   structure detected in step 1 — for a fullstack project with a nested frontend
   dir, `dist/` should be scoped to that dir (e.g. `app/frontend/dist/`) rather
   than matching root-level build output.

   **Starter app (greenfield only).** If the repo has no source yet, also copy
   the stack's runnable skeleton from `templates/<stack>/scaffold/` (TS: a typed
   CLI library; Python: a Django + DRF API; Fullstack: that API plus a React +
   Router frontend) so `make test`/`make lint` pass out of the box. For the
   Fullstack/React choice from step 2: the **minimal harness** is
   `templates/fullstack/frontend/` (configs only); the **full app** is
   `templates/fullstack/scaffold/`. **Never copy the scaffold over existing
   source** — skip any file that already exists.

4. **git pre-commit hook.** Copy `templates/git-hooks/pre-commit` →
   `.sdlc-hooks/pre-commit`, then run `make install-hooks` to symlink it.

5. **GitHub Actions.** Copy `templates/github/workflows/*.yml` →
   `.github/workflows/`. When `code-review.yml` is included, also copy its helper
   `templates/github/workflows/build-review-payload.jq` → `.github/workflows/`
   (the apply job calls it via `jq -f .github/workflows/build-review-payload.jq`). (gates
   `ci.yml`/`security.yml`, the Claude automation
   trio, `pr-status-labels.yml`, and `pr-rebase.yml`) and
   `templates/github/dependabot.yml` → `.github/dependabot.yml`. Skip any
   workflow the user opted out of (e.g. no Semgrep → leave the `semgrep` job out
   of `security.yml`). `pr-rebase.yml` auto-rebases behind PRs onto `main` and
   force-pushes with lease; remind the user to add the GitHub App (preferred) or
   `REBASE_TOKEN` PAT secrets so rebased pushes re-trigger CI (see Prerequisites).

   **Adapt `ci.yml` to the chosen stack and project layout:**

   - **Keep only the jobs for chosen languages** — use this table to decide:

     | Job | Keep when |
     |-----|-----------|
     | `node` | TypeScript / JavaScript |
     | `frontend` | Fullstack (nested frontend dir exists) |
     | `python` | Python |
     | `stylelint` | CSS / SCSS / Sass (independent of TypeScript) |
     | `e2e` | Fullstack (Playwright config present or planned) |

   - **Omit filter keys for languages not in the project** — dead filters slow CI
     and confuse future editors. Drop the corresponding `outputs:` line and
     `paths-filter` entry alongside the job.

   - **Adjust `paths-filter` patterns to match the actual project structure**
     detected in step 1. Replace the template's assumed paths with the real ones:

     | Filter key | Template default | Adapt to |
     |------------|-----------------|----------|
     | `node` | `**/*.ts`, `!app/**` | Remove `!app/**` exclusion if there is no nested Python `app/`; add/remove globs to match where TS source lives |
     | `frontend` | `app/frontend/**` | Replace with the actual nested frontend dir (e.g. `frontend/**`, `client/**`) |
     | `python` | `app/**/*.py`, `app/pyproject.toml` | Replace `app/` with the actual Python source root (e.g. `src/`, `api/`, `.`) |
     | `styles` | `**/*.css`, `**/*.scss`, `**/*.sass` | Usually kept broad; narrow only if CSS lives in one specific subtree |

6. **Hosting (web-app stacks).** For Python/Fullstack, offer the hosting layer:
   copy `templates/<stack>/hosting/` (`Dockerfile`, `.dockerignore`,
   `docker-compose.yml`) to the repo root, `templates/azure/infra/` → `infra/`,
   `templates/azure/workflows/azure-deploy.yml` → `.github/workflows/`, and
   `templates/azure/HOSTING.md`. Local: `docker compose up --build`. Deploy needs
   the Azure OIDC secrets + repo variables in `HOSTING.md` (the deploy job
   no-ops until `AZURE_WEBAPP_NAME` is set). The TS CLI-library stack has no
   hosting layer. Skip if the user declines.

7. **Ensure labels.** Run `scripts/ensure-labels.sh` (idempotent). Creates
   `check-in-progress`, `check-pass`, `check-fail`, `question`, `no-automation`,
   `dependencies`, `security`, `needs-rebase`.

8. **Claude team settings.** Three components — all live under `.claude/` and are
   checked into the repo so every teammate gets the same baseline.

   **a. settings.json** — deep-merge `templates/claude/settings.json` (marketplaces,
   `enabledPlugins`, Stop hook, ponytail `statusLine`, `defaultMode: plan`,
   `alwaysThinkingEnabled`, `includeCoAuthoredBy`, and the output-token env var)
   into the target repo's `.claude/settings.json` (team values win on conflict;
   the repo keeps every other key):

   ```bash
   tmpl=templates/claude/settings.json   # this skill's template
   mkdir -p .claude
   jq -s '.[0] * .[1]' .claude/settings.json "$tmpl" 2>/dev/null || cp "$tmpl" .claude/settings.json
   ```

   **Never clobber silently:** if the repo already sets `statusLine`, `model`, or
   a plugin entry differently, show the diff and ask before overwriting. The
   `statusLine` command assumes a bash-capable shell (`ls`/`sort`/`tail`) and that
   the user has ponytail installed; it self-resolves the newest install, so it
   survives plugin auto-updates.

   **b. CLAUDE.md** — copy `templates/claude/CLAUDE.md` → `.claude/CLAUDE.md` if
   not already present. If it exists, show the diff and offer to merge sections.
   This sets the git commit policy, ambiguity-handling, and prose output-style
   rules for the whole team (the "no filler, no trailing summaries, no AI slop"
   rules that keep Claude's prose from sounding AI-generated). It complements
   Ponytail, which governs code minimalism; CLAUDE.md governs communication style.

   **c. rules/** — copy ONLY the rules relevant to the chosen stack from
   `templates/claude/rules/` → `.claude/rules/`, skipping any file that already
   exists (show diff and ask for conflicts). Selection logic:

   | Rule file | Copy when |
   |-----------|-----------|
   | `coding-guidelines.md` | **Always** (`alwaysApply: true`) |
   | `context7.md` | **Always** — fetches live library docs |
   | `python.md` | Stack includes Python |
   | `js-ts.md` | Stack includes TypeScript or JavaScript |
   | `css.md` | Stack includes CSS/SCSS/Sass (independent of TypeScript) |
   | `sql.md` | Project uses SQL (detected: ORM migration files, `.sql` files, or DB dependency in manifest) |

   Do not copy a rule file if its language is not in use — dead rules load
   noise into every Claude session.

9. **Verify & summarize.** Run `make check` and `make test` locally and report
   results. Summarize what was created/changed and list manual follow-ups: add
   the repo secrets above (incl. Azure OIDC if hosting was added), and
   (recommended) enable branch protection requiring the CI checks.

## Set branch protection (default branch)

`code-review.yml`'s `apply` job pushes `[autofix]` commits, so the default branch must force
changes through a reviewable PR. After the workflows are in place, set protection (replace
`$OWNER`/`$REPO`/`$DEFAULT_BRANCH`):

```bash
gh api -X PUT "repos/$OWNER/$REPO/branches/$DEFAULT_BRANCH/protection" \
  -H "Accept: application/vnd.github+json" --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0, "dismiss_stale_reviews": true },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

- `required_approving_review_count: 0` keeps it usable on **solo personal repos** (GitHub won't
  let you approve your own PR); raise to `1+` once the repo has another reviewer.
- **On failure, warn — do not abort the scaffold.** A **private repo on a free personal plan**
  returns HTTP 403: `Upgrade to GitHub Pro or make this repository public to enable this feature.`
  Catch the non-zero exit, print the **exact status and message**, then continue — e.g.:
  > ⚠️ Could not enable branch protection on `$OWNER/$REPO` (HTTP 403): "Upgrade to GitHub Pro
  > or make this repository public to enable this feature." The `[autofix]` workflow will still
  > run, but nothing enforces that autofix commits are reviewed before reaching `$DEFAULT_BRANCH`.
  > Fix: upgrade to GitHub Pro, make the repo public, or review every `[autofix]` PR by hand.
- Availability: branch protection/rulesets are **free on public repos** (any account); **private
  repos need GitHub Pro** (personal) or **Team/Enterprise** (org). Not an org-only feature.

## Key facts

- `claude-comment-triage.yml` loads the `wp-labs-standards@wp-labs-starter`
  plugin (which provides the `github-pr-review` skill) and hardcodes the
  marketplace `cssherry-wp/wp-labs-starter`.
- `[autofix]` coordination: triage commits are `[autofix]`-prefixed and signed
  `<!-- claude-autofix -->`; `code-review.yml` skips them.
- **Branch protection required:** `code-review.yml`'s `apply` job pushes an
  `[autofix]` commit to the PR branch from an agent-derived patch, and the agent
  runs only on same-repo PRs (forks get no secrets). The scaffolder sets this up
  automatically (see **Set branch protection** above) and MUST NOT auto-merge on
  `[autofix]`/bot authorship — the human-review gate is what bounds a prompt-injected
  patch. On private free-plan repos protection can't be enabled (403); warn and have
  the user review every `[autofix]` PR by hand instead.

## Common mistakes

- Overwriting an existing `package.json`/`pyproject.toml`/`.claude/settings.json`
  instead of merging — always merge.
- Forgetting the `CLAUDE_CODE_OAUTH_TOKEN` secret — the four Claude workflows
  silently no-op or fail without it.
- Scaffolding the Playwright `e2e` job for a backend-only repo — it is for
  frontends; the CI job already no-ops, but don't promise e2e where there's no UI.
