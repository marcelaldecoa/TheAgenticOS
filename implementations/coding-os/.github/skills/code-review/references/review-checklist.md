# Code Review Checklist

Use this checklist for every code review.

## Correctness
- [ ] Does the code do what it claims to do?
- [ ] Are edge cases handled (null, empty, boundary values)?
- [ ] Are error paths complete (what if the DB is down? The API returns 500?)?
- [ ] Are race conditions possible with concurrent access?

## Security
- [ ] Is user input validated before use?
- [ ] Are SQL queries parameterized (no string interpolation)?
- [ ] Are credentials kept out of code (env vars, secrets manager)?
- [ ] Is sensitive data excluded from logs?
- [ ] Are authentication/authorization checks present where needed?

## Quality
- [ ] Is the code consistent with existing project style?
- [ ] Are names descriptive and consistent?
- [ ] Is complexity reasonable (no deeply nested conditionals)?
- [ ] Is there unnecessary duplication?
- [ ] Are functions focused (single responsibility)?

## Testing
- [ ] Are new code paths covered by tests?
- [ ] Do tests verify behavior, not implementation details?
- [ ] Are edge cases tested?
- [ ] Are tests deterministic (no flaky tests)?

## Performance
- [ ] Are there obvious N+1 queries or unnecessary loops?
- [ ] Is caching used where appropriate?
- [ ] Are large data sets handled with pagination/streaming?
