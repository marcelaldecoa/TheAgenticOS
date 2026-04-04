---
name: escalation
description: "Prepare an escalation package for human agents or engineering. Use when an issue exceeds automated resolution capability, requires engineering intervention, or involves a critical customer situation."
---

# Escalation Workflow

## When to Use
- Issue cannot be resolved within the system's autonomy level
- Root cause requires engineering intervention (code fix, infrastructure change)
- Customer is an enterprise account with SLA requirements
- Data loss or security incident suspected

## Procedure

### 1. Compile the Package
Every escalation must include:

```
## Escalation Package

**Ticket ID**: [id]
**Priority**: [critical/high]
**Customer**: [plan] plan, [tenure] tenure

### Summary
[One paragraph: what happened, what was tried, what is needed]

### Investigation Log
1. [step taken] → [result]
2. [step taken] → [result]

### Evidence
- [log entries, error messages, metrics]

### Proposed Fix
[If the fix is known but requires higher privileges]

### Customer Communication
[Draft response ready for human review]
```

### 2. Route
- Infrastructure issues → Engineering on-call
- Billing/account issues → Account management
- Security incidents → Security team (immediate)

### 3. Ensure Continuity
- The escalation must be self-contained — the human must NOT need to re-investigate
- Include all relevant context so the handoff is seamless
