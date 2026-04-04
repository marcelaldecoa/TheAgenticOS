---
description: "Use when writing tests, creating test files, or running test suites. Covers pytest patterns, fixtures, and test organization."
applyTo: ["**/test_*.py", "**/*_test.py", "**/tests/**"]
---

# Testing Standards

- Use `pytest` as the test framework
- Name test files `test_<module>.py` or `<module>_test.py`
- Name test functions `test_<behavior_being_tested>`
- Structure tests as: Arrange → Act → Assert
- One assertion per test when practical
- Use fixtures for shared setup, not setUp/tearDown
- Mock external services — never make real network calls in unit tests
- Test happy path first, then edge cases, then error cases
- Use `pytest.raises` for expected exceptions
- Use `pytest.mark.parametrize` for data-driven tests
