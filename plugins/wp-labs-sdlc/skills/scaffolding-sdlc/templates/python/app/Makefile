# Django + uv SDLC targets.
.PHONY: install lint format check check-python typecheck typecheck-python test test-python install-hooks

install:
	uv sync --extra dev

lint: ; uv run --extra dev ruff check .

format:
	uv run --extra dev ruff format .
	uv run --extra dev ruff check --fix .

# CI mode: no file modifications.
check:
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .

typecheck:
	uv run --extra dev mypy . || echo "WARNING: mypy found issues — review output above"

test: ; uv run --extra dev pytest || [ $$? -eq 5 ]

# Aliases so CI can use one target set across Python and fullstack repos.
check-python: check
typecheck-python: typecheck
test-python: test

install-hooks:
	@if [ -d ../.git ]; then ln -sf ../../.sdlc-hooks/pre-commit ../.git/hooks/pre-commit && echo "pre-commit installed"; else echo "not a git repo"; fi
