# Expand .gitignore for the stack

**Date**: 2026-06-22-1403  
**Commit**: `4f6a51f`

Logic: Cover Node/TS/React build output, test/coverage/e2e artifacts,
Python tooling caches, Docker overrides, env files, and the local Claude
Code settings file so generated and machine-local files stay untracked.

Caveats/assumptions:
- .env.example is force-kept; secrets in .env* are ignored.
