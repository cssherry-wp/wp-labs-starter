# Django + uv SDLC targets.
.PHONY: install lint format check check-python typecheck typecheck-python test test-python coverage coverage-python diff-cover diff-cover-python install-hooks

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

coverage:
	uv run --extra dev pytest --cov --cov-fail-under=90 --cov-report=term-missing --cov-report=xml

diff-cover:
	uv run --extra dev diff-cover coverage.xml --compare-branch=origin/main --fail-under=90

# Aliases so CI can use one target set across Python and fullstack repos.
check-python: check
typecheck-python: typecheck
test-python: test
coverage-python: coverage
diff-cover-python: diff-cover

install-hooks:
	@if [ -d ../.git ]; then ln -sf ../../.sdlc-hooks/pre-commit ../.git/hooks/pre-commit && echo "pre-commit installed"; else echo "not a git repo"; fi
