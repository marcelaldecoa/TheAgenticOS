# Multi-OS Coordination — Copilot Instructions

This workspace demonstrates **Multi-OS Federation** — coordinating independent Agentic Operating Systems.

## Architecture

- **Federation Bus**: Messages route between independent OSs via a standardized protocol.
- **Capability Registry**: Each OS publishes what it can do; others discover and request.
- **Cross-OS Governance**: Data classification enforced at every OS boundary. PII never crosses to lower-clearance systems.

## Available OSs

| OS | Capabilities | Data Clearance |
|----|-------------|----------------|
| **Coding OS** | bug_investigation, feature_development, code_review, deployment | confidential |
| **Research OS** | competitive_analysis, literature_review, market_research | internal |
| **Support OS** | ticket_triage, known_issue_resolution, customer_communication | confidential |
| **Knowledge OS** | documentation_update, knowledge_retrieval, knowledge_validation | internal |

## Cross-OS Rules

- Always redact customer PII before sending data to Research OS or Knowledge OS (internal clearance only)
- Include a correlation ID in every cross-OS message for audit tracing
- When an OS cannot fulfill a request, it must respond with a clear reason — never silently fail
