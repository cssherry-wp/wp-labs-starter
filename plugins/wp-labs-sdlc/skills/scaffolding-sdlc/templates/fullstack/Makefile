# Root Makefile — delegates SDLC targets to app/.
# Add deployment and infrastructure targets here.
.PHONY: install lint lint-python lint-js lint-css format check check-python check-js check-css typecheck typecheck-python test test-python test-js test-e2e install-hooks

install lint lint-python lint-js lint-css format check check-python check-js check-css typecheck typecheck-python test test-python test-js test-e2e install-hooks:
	$(MAKE) -C app $@
