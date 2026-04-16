"""Policy Engine API routes.

Endpoints:
  POST  /policies/rules          — Create a policy rule
  GET   /policies/rules          — List policy rules
  GET   /policies/rules/{id}     — Get a policy rule
  PATCH /policies/rules/{id}     — Update a policy rule (enable/disable, metadata)

No hard DELETE — policies are disabled, not deleted. All changes are audited.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from agr_server.config import settings
from agr_server.models.audit import AuditRecordCreate, AuditResult, AuditSeverity
from agr_server.models.policy import PolicyRule, PolicyRuleCreate, PolicyRuleList, PolicyRuleUpdate
from agr_server.store.base import Store

router = APIRouter(prefix="/policies", tags=["policies"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set. Call set_store() first."
    return _store


async def _audit_policy_change(action: str, policy: PolicyRule, detail: str | None = None) -> None:
    """Emit an audit record for policy changes."""
    await _get_store().append_audit_record(
        AuditRecordCreate(
            agent_id="system:policy-engine",
            action=f"policy.{action}",
            result=AuditResult.SUCCESS,
            intent=f"Policy '{policy.name}' {action}",
            detail=detail or f"Policy {policy.id}: {policy.condition.action_pattern} → {policy.decision}",
            severity=AuditSeverity.WARNING,
        ),
        settings.default_tenant,
    )


@router.post("/rules", response_model=PolicyRule, status_code=201)
async def create_policy(rule: PolicyRuleCreate) -> PolicyRule:
    """Create a new policy rule."""
    policy = await _get_store().create_policy(rule, settings.default_tenant)
    await _audit_policy_change("created", policy)
    return policy


@router.get("/rules", response_model=PolicyRuleList)
async def list_policies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    enabled_only: bool = Query(default=False),
) -> PolicyRuleList:
    """List policy rules."""
    return await _get_store().list_policies(
        settings.default_tenant,
        page=page,
        page_size=page_size,
        enabled_only=enabled_only,
    )


@router.get("/rules/{policy_id}", response_model=PolicyRule)
async def get_policy(policy_id: str) -> PolicyRule:
    """Get a policy rule by ID."""
    policy = await _get_store().get_policy(policy_id, settings.default_tenant)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return policy


@router.patch("/rules/{policy_id}", response_model=PolicyRule)
async def update_policy(policy_id: str, update: PolicyRuleUpdate) -> PolicyRule:
    """Update a policy rule (enable/disable, name, priority, metadata)."""
    policy = await _get_store().update_policy(policy_id, update, settings.default_tenant)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")

    action = "disabled" if update.enabled is False else "updated"
    await _audit_policy_change(action, policy)
    return policy
