---
description: "Use when writing or modifying Python code. Enforces PEP 8, type hints, explicit error handling, and Pydantic for data validation."
applyTo: "**/*.py"
---

# Python Coding Standards

- Follow PEP 8 style guide
- Use type hints on all public function signatures
- Use Pydantic for data validation at API boundaries
- Handle errors explicitly — no bare `except` clauses
- Prefer `raise` with specific exception types
- Use `logging` module, not `print()`, for operational output
- Prefer composition over inheritance
- Keep functions under 30 lines; extract helpers for complex logic
- Use `pathlib.Path` over `os.path` for file operations
