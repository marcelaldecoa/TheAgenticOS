"""Compliance Export API — structured evidence reports.

GET /compliance/export — JSON evidence report for a date range.
This is an evidence report, NOT a compliance assertion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, Query

from agr_server.api.operators import require_role
from agr_server.config import settings
from agr_server.models.dashboard import ComplianceReport, ComplianceSection
from agr_server.store.base import Store

router = APIRouter(prefix="/compliance", tags=["compliance"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set."
    return _store


@router.get("/export", response_model=ComplianceReport)
async def export_compliance(
    since: Optional[datetime] = Query(default=None, description="Period start (ISO 8601)"),
    until: Optional[datetime] = Query(default=None, description="Period end (ISO 8601)"),
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> ComplianceReport:
    """Generate a compliance evidence report for the specified period."""
    await require_role(x_operator_key, "admin", "auditor")
    store = _get_store()
    now = datetime.now(timezone.utc)
    period_start = since or datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    period_end = until or now
    tenant = settings.default_tenant
    gaps = []

    # Agent Inventory
    agent_list = await store.list_agents(tenant, page_size=200)
    agent_items = [a.model_dump(mode="json") for a in agent_list.items]
    agents_without_profile = sum(
        1 for a in agent_list.items
        if not a.access_profile.actions and not a.access_profile.mcps_allowed
    )
    agent_notes = []
    if agents_without_profile > 0:
        agent_notes.append(f"{agents_without_profile} agent(s) have no access profile configured")
        gaps.append("Some agents have no access profile — governance coverage is partial")

    agent_section = ComplianceSection(
        name="Agent Inventory",
        description="All registered agents in the governance plane",
        items=agent_items,
        count=agent_list.total,
        completeness="partial" if agents_without_profile > 0 else "complete",
        notes=agent_notes,
    )

    # Policy Coverage
    from agr_server.models.audit import AuditQuery
    policies = await store.list_policies(tenant, page_size=200)
    policy_items = [p.model_dump(mode="json") for p in policies.items]
    disabled_count = sum(1 for p in policies.items if not p.enabled)
    policy_notes = []
    if disabled_count > 0:
        policy_notes.append(f"{disabled_count} policy(ies) are disabled")

    policy_section = ComplianceSection(
        name="Policy Coverage",
        description="Tenant-wide governance policies",
        items=policy_items,
        count=policies.total,
        completeness="complete",
        notes=policy_notes,
    )

    # Audit Trail
    audit_query = AuditQuery(since=period_start, until=period_end, page_size=1)
    audit_result = await store.query_audit_records(audit_query, tenant)
    audit_section = ComplianceSection(
        name="Audit Trail",
        description=f"Audit records from {period_start.isoformat()} to {period_end.isoformat()}",
        items=[],  # Don't dump all records — just summary
        count=audit_result.total,
        completeness="complete",
        notes=[f"Total records in period: {audit_result.total}"],
    )

    # Approval Records
    approval_stats = await store.get_approval_stats(tenant)
    approval_section = ComplianceSection(
        name="Approval Records",
        description="Human-in-the-loop approval flow statistics",
        items=[approval_stats],
        count=sum([
            approval_stats.get("total_approved", 0),
            approval_stats.get("total_denied", 0),
            approval_stats.get("total_expired", 0),
            approval_stats.get("total_pending", 0),
        ]),
        completeness="complete",
    )

    # Budget Usage
    summary = await store.get_fleet_summary(tenant)
    budget_section = ComplianceSection(
        name="Budget Usage",
        description="Resource consumption tracking status",
        items=[],
        count=0,
        completeness="partial" if summary["total_agents"] > 0 else "not_available",
        notes=["Budget data is per-period; historical aggregation not yet available"],
    )
    if "Budget data" in budget_section.notes[0]:
        gaps.append("Historical budget aggregation not available — per-period snapshots only")

    # Overall completeness
    all_sections = [agent_section, policy_section, audit_section, approval_section, budget_section]
    if any(s.completeness != "complete" for s in all_sections):
        evidence_completeness = "partial" if not gaps else "gaps_detected"
    else:
        evidence_completeness = "complete"

    return ComplianceReport(
        schema_version="1.0.0",
        generated_at=now,
        tenant_id=tenant,
        period_start=period_start,
        period_end=period_end,
        agent_inventory=agent_section,
        policy_coverage=policy_section,
        audit_trail=audit_section,
        approval_records=approval_section,
        budget_usage=budget_section,
        evidence_completeness=evidence_completeness,
        gaps=gaps,
    )
