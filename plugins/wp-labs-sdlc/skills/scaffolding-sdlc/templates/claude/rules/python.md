---
description: Python rules — add to coding-guidelines.md for judgment calls ruff/mypy can't enforce
globs: '*.py'
alwaysApply: false
---

# Python Coding Guidelines

*ruff handles all formatting (Black), imports (isort), naming, and linting (PEP-8 compliance). mypy checks type correctness. See [coding-guidelines](../coding-guidelines.md) for general rules.*

## AI-Prone Mistakes — Always Avoid

- **Never use `eval()` or `exec()`** — prefer safe alternatives
- **Prefer f-strings** over `.format()` or `%` formatting, but keep them readable
- **Functions longer than 40 lines?** Extract. Enforced by [coding-guidelines](../coding-guidelines.md)

## Docstrings (AI Gets This Wrong Often)

Use **Google-style** docstrings for all public functions and classes. Be consistent within the project.

```python
def process_data(input: str, limit: int = 10) -> list[dict]:
    """Process input data with optional limit.

    Args:
        input: The input string to process.
        limit: Maximum number of results to return. Defaults to 10.

    Returns:
        List of processed result dicts.

    Raises:
        ValueError: If limit is negative.
    """
```

## Type Annotations (New Files)

- Use type annotations for **all** function signatures and class attributes in new files
- Match existing style in the file if it already uses hints
- Don't annotate obviously-inferable locals (`x = []` — no annotation needed)

## Testing

- Mirror module structure: `src/foo.py` → `tests/test_foo.py`
- Cover happy path, edge cases, and failure modes (see [coding-guidelines](../coding-guidelines.md))
