# Root Makefile — delegates SDLC targets to app/.
# Add deployment and infrastructure targets here.
.PHONY: install lint lint-python lint-js lint-css format check check-python check-js check-css typecheck typecheck-python test test-python test-js test-e2e coverage coverage-python coverage-js diff-cover diff-cover-python diff-cover-js install-hooks

install lint lint-python lint-js lint-css format check check-python check-js check-css typecheck typecheck-python test test-python test-js test-e2e coverage coverage-python coverage-js diff-cover diff-cover-python diff-cover-js install-hooks:
	$(MAKE) -C app $@
