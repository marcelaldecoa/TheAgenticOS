---
applyTo: "**"
description: "Use when handling cross-OS workflows. Enforces data classification, PII redaction, correlation ID tracking, and audit trail requirements at federation boundaries."
---

# Cross-OS Data Governance

## Data Classification at Boundaries

Before sending data to another OS, check clearance:
- `confidential` data → only to OSs with `confidential` clearance (Coding OS, Support OS)
- `internal` data → any OS
- `public` data → any OS

## PII Redaction

Before sending customer context to `internal`-clearance OSs (Research OS, Knowledge OS):
- Remove: email, phone, address, payment info
- Keep: plan type, tenure, ticket count, category

## Correlation IDs

Every cross-OS workflow gets a UUID correlation ID. Include it in:
- All messages sent between OSs
- All audit log entries
- The final workflow report

## Audit Trail

Log every cross-OS interaction:
```
[timestamp] [correlation_id] [from_os] → [to_os]: [action] [data_classification]
```
