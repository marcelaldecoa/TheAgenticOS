"""Approval Flow API — human-in-the-loop governance.

Endpoints:
  POST /approvals/request        — Create an approval request (idempotent)
  GET  /approvals/pending        — List pending approvals
  POST /approvals/{id}/decide    — Approve or deny (approver/admin role)
  GET  /approvals/{id}           — Check approval status
"""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Header, Query

from agr_server.api.operators import resolve_operator, require_role
from agr_server.config import settings
from agr_server.models.approval import ApprovalDecision, ApprovalList, ApprovalRecord, ApprovalRequestCreate, ApprovalStatus
from agr_server.models.audit import AuditRecordCreate, AuditResult, AuditSeverity
from agr_server.store.base import Store

router = APIRouter(prefix="/approvals", tags=["approvals"])

_store: Store | None = None
APPROVAL_EXPIRY_HOURS = float(os.environ.get("AGR_APPROVAL_EXPIRY_HOURS", "1.0"))
APPROVAL_WEBHOOK_URL = os.environ.get("AGR_APPROVAL_WEBHOOK_URL", "")


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set."
    return _store


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


@router.post("/request", response_model=ApprovalRecord, status_code=201)
async def create_approval(req: ApprovalRequestCreate) -> ApprovalRecord:
    """Create an approval request. Idempotent — returns existing if same context."""
    store = _get_store()
    expires_at = _now() + timedelta(hours=APPROVAL_EXPIRY_HOURS)
    record = await store.create_approval(req, settings.default_tenant, expires_at)

    # Auto-audit
    await store.append_audit_record(
        AuditRecordCreate(
            agent_id=req.agent_id,
            action=f"approval.requested:{req.action}",
            result=AuditResult.SUCCESS,
            intent=req.reason,
            detail=f"Approval {record.id} created for {req.action}",
            severity=AuditSeverity.WARNING,
            metadata={"approval_id": record.id, "triggering_policies": req.triggering_policies},
        ),
        settings.default_tenant,
    )

    # Webhook notification
    if APPROVAL_WEBHOOK_URL:
        try:
            httpx.post(
                APPROVAL_WEBHOOK_URL,
                json={
                    "event": "approval.requested",
                    "approval_id": record.id,
                    "agent_id": req.agent_id,
                    "action": req.action,
                    "reason": req.reason,
                    "expires_at": record.expires_at.isoformat(),
                },
                timeout=5.0,
            )
        except Exception:
            pass  # Best-effort notification

    return record


@router.get("/pending", response_model=ApprovalList)
async def list_pending(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> ApprovalList:
    """List pending approvals (approver/admin role)."""
    await require_role(x_operator_key, "admin", "approver")
    return await _get_store().list_pending_approvals(
        settings.default_tenant, page=page, page_size=page_size,
    )


@router.get("/{approval_id}", response_model=ApprovalRecord)
async def get_approval(approval_id: str) -> ApprovalRecord:
    """Check approval status. No auth required (agents poll this)."""
    record = await _get_store().get_approval(approval_id, settings.default_tenant)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")
    return record


@router.post("/{approval_id}/decide", response_model=ApprovalRecord)
async def decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> ApprovalRecord:
    """Approve or deny an approval request (approver/admin role)."""
    operator = await require_role(x_operator_key, "admin", "approver")
    store = _get_store()

    try:
        record = await store.decide_approval(
            approval_id, decision, decided_by=operator["id"], tenant_id=settings.default_tenant,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if record is None:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")

    # Auto-audit the decision
    await store.append_audit_record(
        AuditRecordCreate(
            agent_id=record.agent_id,
            action=f"approval.{decision.decision.value}:{record.action}",
            result=AuditResult.SUCCESS,
            detail=f"Approval {approval_id} {decision.decision.value} by {operator['name']}",
            severity=AuditSeverity.WARNING,
            metadata={"approval_id": approval_id, "decided_by": operator["id"]},
        ),
        settings.default_tenant,
    )

    return record
