"""Audit trail models — append-only action logging.

Maps to:
- TheAgenticOS Ch.17 (Governance Patterns) — Auditable Action, Signed Intent
- Architecture of Intent (Distributed Trace) — trace propagation across agents
- Architecture of Intent (Structured Execution Log) — per-agent logging

Design decision: Audit records are APPEND-ONLY. No update or delete API exists.
Server-side timestamps and monotonic sequence numbers ensure ordering integrity.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AuditResult(StrEnum):
    """Outcome of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"
    TIMEOUT = "timeout"


class AuditSeverity(StrEnum):
    """Severity classification for audit records."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CostRecord(BaseModel):
    """Resource consumption for a single action."""

    tokens_input: int | None = None
    tokens_output: int | None = None
    monetary_usd: float | None = None
    duration_ms: int | None = None


class AuditRecordCreate(BaseModel):
    """Request body for appending an audit record.

    Trace/span fields are optional — not all agent platforms support them.
    Use ``run_id`` or ``session_id`` as fallback correlation.
    """

    agent_id: str = Field(description="ID of the agent that performed the action")
    action: str = Field(description="Namespaced action (e.g. 'email.send', 'database.query')")
    result: AuditResult

    # Intent context
    intent: str | None = Field(default=None, description="What the agent was trying to accomplish")
    detail: str | None = Field(default=None, description="Additional context or error message")

    # Correlation (multiple options — use what fits your platform)
    trace_id: str | None = Field(default=None, description="Distributed trace ID (OpenTelemetry)")
    span_id: str | None = Field(default=None, description="Span within a trace")
    run_id: str | None = Field(default=None, description="Agent run/execution ID")
    session_id: str | None = Field(default=None, description="Conversation/session ID")
    parent_action_id: str | None = Field(default=None, description="Parent action for chaining")

    # Governance context
    capabilities_exercised: list[str] = Field(default_factory=list)
    approval_id: str | None = Field(default=None, description="Approval reference if action required approval")
    severity: AuditSeverity = AuditSeverity.INFO

    # Cost tracking
    cost: CostRecord | None = None

    # Extension
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditRecord(BaseModel):
    """Full audit record as stored and returned by the API.

    Server-assigned fields: ``sequence``, ``timestamp``, ``tenant_id``.
    """

    sequence: int = Field(description="Monotonic sequence number (server-assigned)")
    timestamp: datetime = Field(description="Server-side timestamp (server-assigned)")
    tenant_id: str = "default"

    # All fields from create request
    agent_id: str
    action: str
    result: AuditResult
    intent: str | None = None
    detail: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    run_id: str | None = None
    session_id: str | None = None
    parent_action_id: str | None = None
    capabilities_exercised: list[str] = Field(default_factory=list)
    approval_id: str | None = None
    severity: AuditSeverity = AuditSeverity.INFO
    cost: CostRecord | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditRecordList(BaseModel):
    """Paginated list of audit records."""

    items: list[AuditRecord]
    total: int
    page: int
    page_size: int
    has_more: bool


class AuditQuery(BaseModel):
    """Query parameters for filtering audit records."""

    agent_id: str | None = None
    action: str | None = None
    result: AuditResult | None = None
    severity: AuditSeverity | None = None
    trace_id: str | None = None
    run_id: str | None = None
    session_id: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
