# wp-labs-starter

A Claude Code **plugin marketplace** for the team. It packages our coding standards, common-task
helpers, and a curated plugin setup so everyone gets the same Claude Code experience from a single
`git` repo.

> Verified against Claude Code **2.1.211**.

## What's inside

This repo is itself the marketplace (`.claude-plugin/marketplace.json`). It ships three plugins:

| Plugin | What it gives you |
|---|---|
| **wp-labs-standards** | Coding-standard skills (`general-coding-guidelines`, `python-style`, `typescript-style`, `css-style`, `sql-style`, `team-docs-convention`) **plus** the common-task workflows `/commit` (structured commit-message format), `change-review` (broad review dispatcher — see [review-skills map](plugins/wp-labs-standards/skills/change-review/review-skills-map.md)), `github-pr-prepare`, and `github-pr-review`. A `PreToolUse` hook also injects the matching standard **deterministically by file type** on every edit (see [Deterministic standards](#deterministic-standards)). |
| **wp-labs-sdlc** `v0.3` | The `scaffolding-sdlc` skill with two modes: **repo mode** bootstraps a repo's full SDLC (runnable starter app, Makefile, pre-commit hook, GitHub Actions CI/security/Claude-PR-automation, Dependabot, PR-status labels, PR auto-rebase, optional hosting with Docker + Azure Bicep); **`--setup-claude` mode** configures the global `~/.claude/` environment on a fresh machine (settings, plugins, `CLAUDE.md`, glob-scoped coding rules). See [Setting up a new machine](#setting-up-a-new-machine). |
| **wp-labs-superpowers** | A fork of [superpowers](https://github.com/obra/superpowers) with our docs-path convention baked in. **Enabled by default** (the stock `superpowers@claude-plugins-official` is disabled to avoid duplicate skill names). See [`plugins/wp-labs-superpowers/FORK.md`](plugins/wp-labs-superpowers/FORK.md). |

We also use a curated set of **external** plugins (see [Recommended setup](#recommended-setup)).

## Setting up a new machine

The fastest path on a fresh machine or new Claude Code install:

```bash
git clone https://github.com/cssherry-wp/wp-labs-starter.git
cd wp-labs-starter
bash plugins/wp-labs-sdlc/skills/scaffolding-sdlc/scripts/setup-claude.sh
```

This writes `~/.claude/settings.json` (marketplaces + plugins), `~/.claude/CLAUDE.md` (commit policy, output style rules), and `~/.claude/rules/` (glob-scoped coding guidelines). Restart Claude Code — it auto-installs any plugin listed in `enabledPlugins` on first launch.

Alternatively, once Claude Code is running, invoke the skill:

```text
/scaffolding-sdlc --setup-claude
```

See [`docs/setting-up-claude-environment.md`](docs/setting-up-claude-environment.md) for full details.

## Quick start (individual)

To add the marketplace and install manually:

```text
/plugin marketplace add cssherry-wp/wp-labs-starter
/plugin install wp-labs-standards@wp-labs-starter
/plugin install wp-labs-sdlc@wp-labs-starter
/plugin install wp-labs-superpowers@wp-labs-starter
```

Then the external plugins:

```text
/plugin install code-review@claude-plugins-official
/plugin install code-simplifier@claude-plugins-official
/plugin install security-guidance@claude-plugins-official
/plugin install explanatory-output-style@claude-plugins-official
/plugin install frontend-design@claude-plugins-official
/plugin install typescript-lsp@claude-plugins-official
/plugin install chrome-devtools-mcp@claude-plugins-official
/plugin install context7@claude-plugins-official
/plugin install claude-md-management@claude-plugins-official
/plugin install playwright@claude-plugins-official
/plugin marketplace add lackeyjb/playwright-skill
/plugin install playwright-skill@playwright-skill
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

Browse or manage everything anytime with `/plugin`.

## Recommended setup

The full recommended config lives in:
[`plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/settings.json`](plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/settings.json)

This is the single source of truth for marketplaces, `enabledPlugins`, the ponytail status-line badge,
the Stop hook, and team-wide Claude settings. The `--setup-claude` mode and the repo scaffold both
deep-merge from this file.

### Default-enabled

`wp-labs-standards`, `wp-labs-sdlc`, `wp-labs-superpowers` (fork), `ponytail`,
`playwright-skill`, `code-review`, `code-simplifier`, `security-guidance`,
`explanatory-output-style`, `frontend-design`, `typescript-lsp`, `chrome-devtools-mcp`,
`context7`, `claude-md-management`, `playwright`.

`superpowers@claude-plugins-official` is explicitly disabled — the fork (`wp-labs-superpowers`)
replaces it. Never enable both (duplicate skill names).

### Opt-in (available, not enabled by default)

| Plugin | Add it when |
|---|---|
| `ralph-loop@claude-plugins-official` | You want the autonomous loop runner (`/ralph-loop`). Better as an individual opt-in — easy to trigger accidentally if always enabled. |
| `superpowers@claude-plugins-official` | You want stock superpowers without our docs-path convention. Disable `wp-labs-superpowers` first. |

## Notes

### Deterministic standards

Skills are model-invoked from their `description`, so language standards only *usually* load.
To make them fire reliably, the `wp-labs-standards` plugin ships a `PreToolUse` hook
(`hooks/inject-standards.js`) on `Edit|Write|MultiEdit`: it reads the target file's extension
and injects the matching standard on **every** edit — no model judgment involved.

- `.py` → `python-style`
- `.ts/.tsx/.js/.jsx/.mjs/.cjs` → `typescript-style`
- `.css/.scss/.sass` → `css-style`

The hook reads the same `SKILL.md` files (single source of truth — no duplicated content). The
skills also stay model-invocable, which covers reviewing/discussing these files when no edit
happens (the hook only fires on edits).

**SQL is deliberately excluded** from the hook: the `.sql` extension is an unreliable signal
(SQL is often embedded in `.py`/`.ts` and migration files), so `sql-style` remains a normal
model-invoked skill. `general-coding-guidelines` and `team-docs-convention` are likewise
skill-only (not file-type specific).

The hook runs on `node` (always present wherever Claude Code runs), so there's no extra
dependency to install.

### CLAUDE.md and rules/

The `scaffolding-sdlc` templates include:

- **`CLAUDE.md`** — git commit policy, ambiguity handling, and prose output style rules (no
  filler language, no em-dashes, no hype, honest specificity). Written into `.claude/CLAUDE.md`
  per repo or `~/.claude/CLAUDE.md` globally via `--setup-claude`.
- **`rules/`** — six glob-scoped rule files that Claude loads automatically for matching file
  types: `coding-guidelines.md` (always-on), `python.md`, `js-ts.md`, `css.md`, `sql.md`,
  `context7.md`.

### superpowers: fork (default) vs stock (opt-in)

`wp-labs-superpowers` is the default: it has our docs-path convention baked in (specs to
`.superpowers/01-specs/`, plans to `.superpowers/02-plans/`). The stock
`superpowers@claude-plugins-official` is disabled in the team template. If you prefer stock
superpowers, disable the fork and enable the stock one — but never run both.

### If you already have personal copies of these skills

`wp-labs-standards` provides `github-pr-prepare` and `github-pr-review`. If you also keep personal
copies in `~/.claude/skills/`, remove the personal copies to avoid duplicate skill names once the
plugin is enabled.

## Maintaining

- Bump a plugin's `version` in its `.claude-plugin/plugin.json` when you change it; the team picks
  up changes on `/plugin update` (or `/plugin marketplace update wp-labs-starter`).
- The superpowers fork refreshes itself: a weekly GitHub Actions workflow
  ([`.github/workflows/refresh-superpowers-fork.yml`](.github/workflows/refresh-superpowers-fork.yml))
  tracks the superpowers snapshot pinned by `anthropics/claude-plugins-official` and opens a PR when
  a new version appears. Run it on demand from the Actions tab, or locally via
  `scripts/refresh-superpowers-fork.sh` (see [`FORK.md`](plugins/wp-labs-superpowers/FORK.md)).
