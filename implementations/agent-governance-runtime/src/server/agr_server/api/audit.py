"""Audit Trail API routes — APPEND-ONLY.

Endpoints:
  POST /audit/records                — Append an audit record
  GET  /audit/records                — Query audit trail (paginated)
  GET  /audit/agents/{id}/records    — Agent-specific audit trail
  GET  /audit/traces/{trace_id}      — Reconstruct full trace

Design: No PUT/PATCH/DELETE endpoints exist. Audit records are immutable
once written. This is a deliberate governance decision.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from agr_server.config import settings
from agr_server.models.audit import (
    AuditQuery,
    AuditRecord,
    AuditRecordCreate,
    AuditRecordList,
    AuditResult,
    AuditSeverity,
)
from agr_server.store.base import Store

router = APIRouter(prefix="/audit", tags=["audit"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set. Call set_store() first."
    return _store


@router.post("/records", response_model=AuditRecord, status_code=201)
async def append_audit_record(record: AuditRecordCreate) -> AuditRecord:
    """Append an audit record. Server assigns sequence number and timestamp."""
    return await _get_store().append_audit_record(record, settings.default_tenant)


@router.get("/records", response_model=AuditRecordList)
async def query_audit_records(
    agent_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    result: AuditResult | None = Query(default=None),
    severity: AuditSeverity | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> AuditRecordList:
    """Query audit records with filtering and pagination."""
    query = AuditQuery(
        agent_id=agent_id,
        action=action,
        result=result,
        severity=severity,
        trace_id=trace_id,
        run_id=run_id,
        session_id=session_id,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
    )
    return await _get_store().query_audit_records(query, settings.default_tenant)


@router.get("/agents/{agent_id}/records", response_model=AuditRecordList)
async def get_agent_audit_trail(
    agent_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> AuditRecordList:
    """Get the audit trail for a specific agent."""
    return await _get_store().get_agent_audit_trail(
        agent_id, settings.default_tenant, page=page, page_size=page_size
    )


@router.get("/traces/{trace_id}", response_model=list[AuditRecord])
async def get_trace(trace_id: str) -> list[AuditRecord]:
    """Reconstruct a full distributed trace across agents."""
    return await _get_store().get_trace(trace_id, settings.default_tenant)
