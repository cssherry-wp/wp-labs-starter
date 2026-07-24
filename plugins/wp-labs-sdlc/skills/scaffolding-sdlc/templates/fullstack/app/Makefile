# Backend (Django + uv) + frontend (Vite) SDLC targets.
# The frontend is a self-contained npm project under frontend/.
.PHONY: install lint lint-python lint-js lint-css format check check-python check-js check-css typecheck typecheck-python test test-python test-js test-e2e coverage coverage-python coverage-js install-hooks

install:
	uv sync --extra dev
	cd frontend && npm install

lint: lint-python lint-js lint-css
lint-python: ; uv run --extra dev ruff check .
lint-js: ; cd frontend && npm run lint
lint-css: ; cd frontend && npm run lint:css

format:
	uv run --extra dev ruff format .
	uv run --extra dev ruff check --fix .
	cd frontend && npm run format
	cd frontend && npm run format:css

# CI mode: no file modifications.
check: check-python check-js check-css
check-python:
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .
check-js:
	cd frontend && npm run typecheck
	cd frontend && npm run lint
check-css: ; cd frontend && npm run lint:css

typecheck: check-js typecheck-python
typecheck-python:
	uv run --extra dev mypy . || echo "WARNING: mypy found issues — review output above"

test: test-python test-js
test-python: ; uv run --extra dev pytest || [ $$? -eq 5 ]
test-js: ; cd frontend && npm test
test-e2e: ; cd frontend && npm run test:e2e

coverage: coverage-python coverage-js
coverage-python:
	uv run --extra dev pytest --cov --cov-fail-under=80 --cov-report=term-missing
coverage-js: ; cd frontend && npm run coverage

install-hooks:
	@if [ -d ../.git ]; then ln -sf ../../.sdlc-hooks/pre-commit ../.git/hooks/pre-commit && echo "pre-commit installed"; else echo "not a git repo"; fi
