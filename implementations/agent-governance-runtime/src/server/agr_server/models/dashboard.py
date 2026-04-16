"""Dashboard and compliance export models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Dashboard Models ---

class FleetSummary(BaseModel):
    """Fleet-wide summary statistics."""

    total_agents: int = 0
    agents_by_status: dict[str, int] = Field(default_factory=dict)
    agents_by_platform: dict[str, int] = Field(default_factory=dict)
    active_last_24h: int = 0
    total_audit_records: int = 0
    total_policies: int = 0
    total_policies_enabled: int = 0


class TopConsumer(BaseModel):
    """Agent ranked by consumption."""

    agent_id: str
    agent_name: str | None = None
    platform: str | None = None
    requests: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0


class Violation(BaseModel):
    """A governance violation (denied action)."""

    timestamp: str
    agent_id: str
    action: str
    decision: str
    reason: str | None = None
    matched_policy_ids: list[str] = Field(default_factory=list)


class ApprovalStats(BaseModel):
    """Approval flow statistics."""

    total_pending: int = 0
    total_approved: int = 0
    total_denied: int = 0
    total_expired: int = 0
    avg_response_minutes: float | None = None


# --- Compliance Export Models ---

class ComplianceSection(BaseModel):
    """A section of the compliance report."""

    name: str
    description: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    completeness: str = Field(
        default="complete",
        description="complete | partial | not_available",
    )
    notes: list[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    """Structured compliance evidence report.

    This is an evidence report, NOT a compliance assertion.
    It reports what AGR knows — completeness flags indicate gaps.
    """

    schema_version: str = "1.0.0"
    generated_at: datetime
    tenant_id: str
    period_start: datetime
    period_end: datetime

    # Evidence sections
    agent_inventory: ComplianceSection
    policy_coverage: ComplianceSection
    audit_trail: ComplianceSection
    approval_records: ComplianceSection
    budget_usage: ComplianceSection

    # Overall
    evidence_completeness: str = Field(
        description="complete | partial | gaps_detected"
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Known evidence gaps",
    )
