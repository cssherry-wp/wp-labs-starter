<!-- wp-labs team overlay: BEGIN -->

## Diff Coverage Check

After all tests pass, run the coverage gap report and share the output with the user:

```bash
make diff-cover         # TypeScript
make diff-cover-python  # Python
```

For each uncovered line, triage by whether the gap is obvious:

**Obvious gap (fix without asking):** logic that can clearly fail — a conditional branch, data validation, error path, or business rule. Write the failing test and follow the TDD cycle.

**Non-obvious gap (ask the user):** show the file, line number, and code, then explain *why it may not have been covered* and ask whether to add a test. Common reasons:

| Reason | Typical lines |
|--------|---------------|
| Reachable only via untested input combination | Guards with multiple conditions |
| Defensive safety net, likely unreachable | `raise RuntimeError("unreachable")`, exhaustive `else` |
| Generated / boilerplate with no custom logic | Auto-generated migrations, `__str__`, scaffolded serializer fields |
| 3rd party framework behaviour | `super().save()`, framework-provided validation, ORM field declarations |
| Pure orchestration, covered by e2e | View/controller that delegates entirely to already-tested services; no conditional logic of its own |
| UI-layer error path, covered by e2e | Frontend error display, form validation messages |

Do not skip this step. Every gap needs a decision — silence is not an answer.

## Test Conventions

### Co-locate Tests With Source
Keep the test file next to the source file in every language:
- JavaScript/React: `Button.test.jsx` next to `Button.jsx`
- Go: `foo_test.go` next to `foo.go`
- Python: `test_foo.py` next to `foo.py`

### Cover Invalid Input

- **Unit tests:** cover all edge cases and invalid input — empty strings, nulls, boundary values, invalid formats, and unexpected types.
- **e2e tests:** verify that error scenarios display and are captured correctly, not to retest business logic. Confirm the UI surfaces the right error state; the unit layer owns the logic underneath.

### Mocking Policy
Minimize mocks — use them only at true system boundaries: databases, HTTP clients, filesystems, clocks, and external processes. Mock the I/O boundary, not the logic above it.

<!-- wp-labs team overlay: END -->
