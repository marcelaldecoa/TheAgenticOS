---
name: fix-bug
description: "Fix a bug in the codebase. Use when debugging, diagnosing failures, fixing errors, resolving issues, or investigating unexpected behavior."
---

# Bug Fix Workflow

## When to Use
- A bug is reported or observed
- A test is failing unexpectedly
- Unexpected behavior needs diagnosis

## Procedure

### 1. Reproduce
- Read the bug report or error message
- Identify the code path involved
- Write a failing test that demonstrates the bug
- Confirm the test fails for the right reason

### 2. Diagnose
- Trace the execution path from the failing test
- Identify where actual behavior diverges from expected
- Check recent changes (`git log`, `git diff`) for potential causes
- Check if similar bugs have occurred nearby

### 3. Fix
- Make the **minimal change** that fixes the root cause
- Do NOT refactor surrounding code (separate concern)
- Follow existing code patterns and style

### 4. Verify
- Run the failing test — it should now pass
- Run the full test suite — no regressions
- If applicable, run linters and type checkers

### 5. Document
- Write a clear commit message: what was wrong, why, and what was changed
- If the bug class could recur, add a comment explaining the invariant

## Anti-Patterns
- Fixing symptoms instead of root cause
- Making large refactors alongside a bug fix
- Skipping the reproduction step

## Resources
- [Bug report template](./references/bug-report-template.md) — use when documenting the fix
