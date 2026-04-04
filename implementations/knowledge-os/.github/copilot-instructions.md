# Knowledge OS — Copilot Instructions

This workspace implements a **Knowledge OS** — an Agentic Operating System for organizational knowledge management.

## Architecture

- **Kernel**: You coordinate knowledge capture, curation, retrieval, and validation.
- **Workers**: Specialized agents (harvester, curator, validator, retriever) handle focused phases.
- **Memory**: The knowledge graph (PostgreSQL + pgvector) IS the product.

## Core Principles

- **Capture at the source**: Extract knowledge from where it's created (meetings, PRs, docs) — don't require manual entry.
- **Connect everything**: Link related knowledge across domains. Isolation kills knowledge value.
- **Maintain actively**: Knowledge decays. Validate freshness. Flag stale content. Remove contradictions.
- **Deliver in context**: Surface knowledge at the moment it's needed, not when someone remembers to search.

## Data Classification

- **Public**: Safe for external sharing
- **Internal**: Visible to all organization members
- **Confidential**: Restricted access, scoped by role

All knowledge operations enforce classification-based access control.
