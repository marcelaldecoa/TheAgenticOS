# Bug Report Template

Use this template when documenting a bug fix.

## Bug Report

**Reported**: [date]
**Severity**: [critical / major / minor]
**Component**: [affected module/file]

## Reproduction

**Steps to reproduce**:
1. [step]
2. [step]
3. [step]

**Expected behavior**: [what should happen]
**Actual behavior**: [what happens instead]

## Diagnosis

**Root cause**: [why it happens]
**Evidence**: [log entries, stack traces, failing test output]

## Fix

**Files changed**: [list]
**Approach**: [what was changed and why]
**Risk**: [what could go wrong with this fix]

## Verification

- [ ] Failing test written BEFORE fix
- [ ] Test passes AFTER fix
- [ ] Full test suite passes (no regressions)
- [ ] Related edge cases checked
