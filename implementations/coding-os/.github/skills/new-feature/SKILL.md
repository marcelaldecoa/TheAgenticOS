---
name: new-feature
description: "Implement a new feature end-to-end. Use when adding functionality, creating endpoints, building components, or implementing user stories."
---

# New Feature Workflow

## When to Use
- Adding new functionality to the codebase
- Implementing a user story or feature request
- Creating new API endpoints, UI components, or services

## Procedure

### 1. Understand Requirements
- Parse the feature request for surface intent, operational constraints, and boundary conditions
- Clarify ambiguities BEFORE writing code (ask the user)
- Identify affected areas of the codebase

### 2. Analyze Existing Patterns
- Search for similar features in the codebase
- Read existing code in the affected modules
- Note the conventions: naming, structure, error handling, testing patterns

### 3. Plan Implementation
For anything beyond a single-file change, produce a plan:
```
## Plan
- [ ] Step 1: What to do, where
- [ ] Step 2: What to do, where
- [ ] Step 3: Tests
```

### 4. Implement
- **Delegate to @coder** for the implementation
- Work incrementally — one logical unit at a time
- Follow existing patterns strictly

### 5. Test
- **Delegate to @tester** for test creation
- Unit tests for new functions
- Integration tests for new endpoints/workflows
- Edge case coverage

### 6. Review
- **Delegate to @reviewer** for quality check
- Address all critical and major findings
- Re-run tests after addressing findings

### 7. Deliver
- Summarize what was built
- List all files created/modified
- Note any follow-up work needed

## Coordination
This skill uses all three specialist agents:
1. `@coder` — writes the implementation
2. `@tester` — writes and runs tests
3. `@reviewer` — reviews the complete change

## Resources
- [Feature specification template](./references/feature-spec-template.md) — use for the planning step
