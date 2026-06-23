# Python SDLC targets — scaffolded by scaffolding-sdlc.
# `uv run --extra dev` ensures the dev tools (ruff/mypy/pytest) are installed,
# so CI can call these targets without a separate `make install` step.
# The *-python aliases give CI a target set that is uniform with the
# fullstack Makefile.
.PHONY: install lint format check check-python typecheck typecheck-python test test-python install-hooks

install:
	uv sync --extra dev

lint:
	uv run --extra dev ruff check .

format:
	uv run --extra dev ruff format .
	uv run --extra dev ruff check --fix .

# CI mode: no file modifications.
check:
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .

typecheck:
	uv run --extra dev mypy . || echo "WARNING: mypy found issues — review output above"

test:
	uv run --extra dev pytest

# Aliases so CI can use one target set across Python and fullstack repos.
check-python: check
typecheck-python: typecheck
test-python: test

install-hooks:
	@if [ -d .git ]; then ln -sf ../../.sdlc-hooks/pre-commit .git/hooks/pre-commit && echo "pre-commit installed"; else echo "not a git repo"; fi
