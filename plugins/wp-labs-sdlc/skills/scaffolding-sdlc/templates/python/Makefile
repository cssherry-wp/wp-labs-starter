# Root Makefile — delegates SDLC targets to app/.
# Add deployment and infrastructure targets here.
.PHONY: install lint format check check-python typecheck typecheck-python test test-python coverage coverage-python diff-cover diff-cover-python install-hooks

install lint format check check-python typecheck typecheck-python test test-python coverage coverage-python diff-cover diff-cover-python install-hooks:
	$(MAKE) -C app $@
