# Escalation Package Template

## Escalation

**Ticket ID**: [ticket-id]
**Priority**: [critical / high]
**Escalated At**: [timestamp]
**Correlation ID**: [if cross-OS]

## Customer Context

| Field | Value |
|-------|-------|
| **Plan** | [plan type] |
| **Tenure** | [months/years] |
| **Recent Tickets** | [count in last 30 days] |
| **Sentiment** | [frustrated / neutral] |

> ⚠️ No PII included. Refer to ticket system for customer contact details.

## Issue Summary

[One paragraph: what the customer reported, what was observed]

## Investigation Log

| Step | Action | Result |
|------|--------|--------|
| 1 | [what was checked] | [what was found] |
| 2 | [what was checked] | [what was found] |
| 3 | [what was checked] | [what was found] |

## Root Cause

[Identified root cause, or "Under investigation — requires engineering diagnosis"]

## Evidence

```
[Log entries, error messages, or metrics that support the diagnosis]
```

## Proposed Fix

[If known — what needs to be done, estimated impact, rollback plan]

## Customer Communication Draft

> Hi [Name],
>
> [Draft response ready for human review before sending]

## Routing

- [ ] Infrastructure issue → Engineering on-call
- [ ] Billing/account issue → Account management
- [ ] Security incident → Security team (immediate)
