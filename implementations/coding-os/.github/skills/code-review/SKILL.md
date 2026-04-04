---
name: code-review
description: "Perform a comprehensive code review. Use when reviewing PRs, assessing code quality, checking for security issues, or validating changes before merge."
---

# Code Review Workflow

## When to Use
- Reviewing a pull request or set of changes
- Assessing code quality before merge
- Security review of sensitive code paths

## Procedure

### 1. Gather Context
- Read the changed files and their surrounding context
- Understand the intent of the change (PR description, commit messages)
- Check that tests exist for the changes

### 2. Review Dimensions

#### Correctness
- Does the code do what it claims?
- Are edge cases handled?
- Are error paths complete?

#### Security
- Input validation on all boundaries
- No credential exposure
- No injection vulnerabilities (SQL, command, path)
- Appropriate authentication/authorization checks

#### Quality
- Consistent with project style
- No unnecessary complexity
- No code duplication
- Clear naming

#### Testing
- Are new code paths tested?
- Are edge cases covered?
- Do tests verify behavior, not implementation?

### 3. Produce Report
Delegate to `@reviewer` for the detailed assessment.

### 4. Follow Up
- If critical issues found: list them clearly, suggest fixes
- If approved: state what was reviewed and why it's acceptable

## Output
A structured review with findings by severity (Critical > Major > Minor) and an overall recommendation (Approve / Request Changes).
