# Fullstack (Python backend + React/Vite frontend) SDLC targets.
# The frontend is a self-contained npm project under frontend/.
.PHONY: install lint lint-python lint-js lint-css format check check-python check-js check-css typecheck test test-python test-js test-e2e install-hooks

install:
	uv sync --extra dev
	cd frontend && npm install

lint: lint-python lint-js lint-css
lint-python: ; uv run ruff check .
lint-js: ; cd frontend && npm run lint
lint-css: ; cd frontend && npx stylelint "src/**/*.scss" --allow-empty-input

format:
	uv run ruff format .
	uv run ruff check --fix .
	cd frontend && npm run format
	cd frontend && npx stylelint --fix "src/**/*.scss" --allow-empty-input

# CI mode: no file modifications.
check: check-python check-js check-css
check-python:
	uv run ruff check .
	uv run ruff format --check .
check-js:
	cd frontend && npm run typecheck
	cd frontend && npm run lint
check-css: ; cd frontend && npx stylelint "src/**/*.scss" --allow-empty-input

typecheck: check-js
	uv run mypy . || echo "WARNING: mypy found issues — review output above"

test: test-python test-js
test-python: ; uv run pytest
test-js: ; cd frontend && npm test
test-e2e: ; cd frontend && npm run test:e2e

install-hooks:
	@if [ -d .git ]; then ln -sf ../../.sdlc-hooks/pre-commit .git/hooks/pre-commit && echo "pre-commit installed"; else echo "not a git repo"; fi
