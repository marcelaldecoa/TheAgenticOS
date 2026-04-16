"""Dashboard API — Fleet statistics for CISOs and governance admins.

Endpoints:
  GET /dashboard/summary         — Fleet-wide summary
  GET /dashboard/top-consumers   — Top agents by resource consumption
  GET /dashboard/violations      — Recent governance violations
  GET /dashboard/approvals       — Approval flow statistics
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, Query

from agr_server.api.operators import require_role
from agr_server.config import settings
from agr_server.models.dashboard import ApprovalStats, FleetSummary, TopConsumer, Violation
from agr_server.store.base import Store

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set."
    return _store


@router.get("/summary", response_model=FleetSummary)
async def fleet_summary(
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> FleetSummary:
    """Fleet-wide summary statistics."""
    await require_role(x_operator_key, "admin", "approver", "auditor")
    data = await _get_store().get_fleet_summary(settings.default_tenant)
    return FleetSummary(**data)


@router.get("/top-consumers", response_model=list[TopConsumer])
async def top_consumers(
    limit: int = Query(default=10, ge=1, le=100),
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> list[TopConsumer]:
    """Top agents by resource consumption."""
    await require_role(x_operator_key, "admin", "approver", "auditor")
    data = await _get_store().get_top_consumers(settings.default_tenant, limit=limit)
    return [TopConsumer(**d) for d in data]


@router.get("/violations", response_model=list[Violation])
async def violations(
    limit: int = Query(default=50, ge=1, le=500),
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> list[Violation]:
    """Recent governance violations (denied actions)."""
    await require_role(x_operator_key, "admin", "approver", "auditor")
    data = await _get_store().get_recent_violations(settings.default_tenant, limit=limit)
    return [Violation(**d) for d in data]


@router.get("/approvals", response_model=ApprovalStats)
async def approval_stats(
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> ApprovalStats:
    """Approval flow statistics."""
    await require_role(x_operator_key, "admin", "approver", "auditor")
    data = await _get_store().get_approval_stats(settings.default_tenant)
    return ApprovalStats(**data)
