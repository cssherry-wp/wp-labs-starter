# Setting Up Project SDLC

**Goal:** Scaffold CI, linting, testing, and pre-commit hooks into a new project using the `scaffolding-sdlc` skill.

## When to use this

- New Django + React (fullstack) or Python-only project
- Existing project that needs CI, linting, or hook standardization
- Adopting the team's `app/` project layout convention

## Assumed project layout

The scaffold targets the `app/` wrapper convention used across wp-labs projects:

```
repo/
  app/                   # all application code
    frontend/            # Vite + React (fullstack only)
    api/                 # Django app packages
    config/              # Django project settings
    manage.py
    pyproject.toml
  Makefile               # delegates to app/Makefile
  .github/
    workflows/
    dependabot.yml
```

The root `Makefile` delegates every SDLC target (`make lint`, `make test`, etc.) to `app/Makefile` via `$(MAKE) -C app $@`. Deployment and infra targets live only in the root `Makefile`.

## Run the skill

In a Claude Code session inside the target repo:

```
/scaffolding-sdlc
```

Claude walks through each component and applies diffs interactively.

## What gets scaffolded

### CI (`plugins/.../templates/github/workflows/ci.yml`)

Five jobs, each skippable via `dorny/paths-filter`:

| Job | Trigger filter | What it runs |
|-----|---------------|--------------|
| `node` | `**/*.ts`, `**/*.js`, `package*.json` (root, not `app/`) | `make lint`, `make typecheck`, `make test` |
| `frontend` | `app/frontend/**` | `npm run lint`, `npm run typecheck`, `npm test` |
| `python` | `app/**/*.py`, `app/pyproject.toml` | `make check-python`, `make typecheck-python`, `make test-python` |
| `stylelint` | `**/*.css`, `**/*.scss`, `**/*.sass` | `npm run lint:css` in `app/frontend/` (or root) |
| `e2e` | `**` minus `**/*.md` | Playwright in `app/frontend/playwright.config.ts` (or root) |

Each job detects whether the relevant config file exists at runtime (e.g. `app/pyproject.toml`, `app/frontend/package.json`) and skips with a summary annotation if not found.

### Dependabot (`templates/github/dependabot.yml`)

Groups updates by ecosystem: `npm-production`, `npm-development`, `pip-production`, `pip-development`, and `actions`. This keeps automated PRs to a manageable count.

### Dependabot automerge (`workflows/dependabot-automerge.yml`)

Watches CI via `gh pr checks --watch`, then squash-merges patch and minor bumps automatically. Major version bumps always go to manual review.

### App-level Makefile (`app/Makefile`)

All actual SDLC commands live here:

- `make install` — `uv sync --extra dev` + `cd frontend && npm install`
- `make lint` — ruff + biome + stylelint
- `make format` — ruff format + biome write + stylelint --fix
- `make check` / `make check-python` / `make check-js` / `make check-css` — CI-mode (no file writes)
- `make typecheck` / `make typecheck-python` — mypy + biome typecheck
- `make test` / `make test-python` / `make test-js` / `make test-e2e` — pytest + Vitest + Playwright
- `make install-hooks` — symlinks `.sdlc-hooks/pre-commit` into `../.git/hooks/`

### Frontend tooling (`app/frontend/`)

`package.json` includes two CSS scripts:

- `lint:css` — `stylelint "src/**/*.scss" --allow-empty-input`
- `format:css` — `stylelint --fix "src/**/*.scss" --allow-empty-input`

Dependencies: `stylelint`, `stylelint-config-standard-scss`, `sass`.

Config: `stylelint.config.js` extending `stylelint-config-standard-scss`.

## Adapting after scaffolding

**No SCSS yet:** the `lint:css` and `format:css` scripts use `--allow-empty-input`, so they're safe to leave in place — they no-op until `.scss` files exist.

**Python-only project:** use the `python` template. It omits `app/frontend/` and the frontend Makefile targets. The CI `frontend` and `stylelint` jobs self-skip at runtime.

**pyproject-tooling merge step:** after scaffolding, the `pyproject.toml` merge targets `app/pyproject.toml`. Verify the merge script points to `app/` (tracked separately; see SKILL.md).
