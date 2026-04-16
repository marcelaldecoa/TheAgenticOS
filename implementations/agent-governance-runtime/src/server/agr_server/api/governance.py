"""Unified Governance Evaluation API.

POST /governance/evaluate — THE authoritative decision point.

Combines: agent status + access profile + tenant policies + budget status
into a single governance decision. All enforcement flows through here.
"""

from __future__ import annotations

import fnmatch

from fastapi import APIRouter, Header, HTTPException

from agr_server.config import settings
from agr_server.models.agent import AccessDecision
from agr_server.models.audit import AuditRecordCreate, AuditResult, AuditSeverity
from agr_server.models.policy import PolicyEvalRequest, PolicyEvalResponse, PolicyMatch
from agr_server.store.base import Store

router = APIRouter(prefix="/governance", tags=["governance"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set. Call set_store() first."
    return _store


def _match_action_pattern(pattern: str, action: str) -> bool:
    """Match an action against a pattern. Supports '*' and dotted wildcards.

    Examples:
        'deploy.production' matches 'deploy.production' (exact)
        'deploy.*' matches 'deploy.production' (wildcard)
        '*' matches anything
    """
    if pattern == action:
        return True
    return fnmatch.fnmatch(action, pattern)


@router.post("/evaluate", response_model=PolicyEvalResponse)
async def evaluate(
    request: PolicyEvalRequest,
    authorization: str | None = Header(default=None),
) -> PolicyEvalResponse:
    """Evaluate an action against all governance controls.

    Decision flow:
    1. Resolve agent identity (from request or token)
    2. Check agent status (must be active)
    3. Evaluate agent's access profile
    4. Evaluate tenant-wide policies
    5. Check budget status
    6. Return most restrictive decision

    Precedence: deny > require_approval > allow
    """
    store = _get_store()

    # 1. Resolve agent — prefer token-based identity
    agent_id = request.agent_id
    if authorization:
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization
        agent = await store.get_agent_by_token(token)
        if agent is None:
            raise HTTPException(status_code=401, detail="Invalid agent token")
        agent_id = agent.id
    else:
        agent = await store.get_agent(agent_id, settings.default_tenant)

    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    matched_rules: list[PolicyMatch] = []
    final_decision = AccessDecision.ALLOW
    reason_parts: list[str] = []

    # 2. Check agent status
    if agent.status != "active":
        # Auto-audit
        await _audit_governance_decision(agent_id, request.action, "denied", f"Agent status: {agent.status}")
        return PolicyEvalResponse(
            decision=AccessDecision.DENY,
            reason=f"Agent status is '{agent.status}', must be 'active'",
            agent_status=agent.status,
        )

    # 3. Evaluate agent access profile
    profile_decision = agent.access_profile.check_action(request.action)
    if profile_decision == AccessDecision.DENY:
        final_decision = AccessDecision.DENY
        reason_parts.append(f"Access profile: {request.action} → deny")
    elif profile_decision == AccessDecision.REQUIRE_APPROVAL:
        if final_decision != AccessDecision.DENY:
            final_decision = AccessDecision.REQUIRE_APPROVAL
        reason_parts.append(f"Access profile: {request.action} → require_approval")

    # 4. Evaluate tenant policies (most restrictive wins)
    policies = await store.get_enabled_policies(settings.default_tenant)
    for policy in policies:
        if not _match_action_pattern(policy.condition.action_pattern, request.action):
            continue

        # Check platform filter
        if policy.condition.platforms and agent.platform not in policy.condition.platforms:
            continue

        # Check environment filter
        if policy.condition.environments:
            agent_env = agent.deployment.environment if agent.deployment else None
            if agent_env not in policy.condition.environments:
                continue

        matched_rules.append(PolicyMatch(
            policy_id=policy.id,
            policy_name=policy.name,
            decision=policy.decision,
            priority=policy.priority,
            matched_pattern=policy.condition.action_pattern,
        ))

        # Apply most-restrictive-wins
        if policy.decision == AccessDecision.DENY:
            final_decision = AccessDecision.DENY
            reason_parts.append(f"Policy '{policy.name}': {request.action} → deny")
        elif policy.decision == AccessDecision.REQUIRE_APPROVAL:
            if final_decision != AccessDecision.DENY:
                final_decision = AccessDecision.REQUIRE_APPROVAL
                reason_parts.append(f"Policy '{policy.name}': {request.action} → require_approval")

    # 5. Check budget
    budget_status = await store.get_budget_status(agent_id, settings.default_tenant)
    budget_detail = None
    if budget_status.status == "exceeded":
        # Hard enforcement on request limits
        if budget_status.max_requests_per_hour and budget_status.hourly_usage:
            if budget_status.hourly_usage.requests >= budget_status.max_requests_per_hour:
                final_decision = AccessDecision.DENY
                reason_parts.append("Budget: request limit exceeded")
        budget_detail = "; ".join(budget_status.warnings)
    elif budget_status.warnings:
        budget_detail = "; ".join(budget_status.warnings)

    if not reason_parts:
        reason_parts.append("No restrictions apply")

    reason = "; ".join(reason_parts)

    # Auto-audit the governance decision
    await _audit_governance_decision(agent_id, request.action, final_decision.value, reason)

    return PolicyEvalResponse(
        decision=final_decision,
        reason=reason,
        matched_rules=matched_rules,
        agent_status=agent.status,
        budget_status=budget_status.status,
        budget_detail=budget_detail,
    )


async def _audit_governance_decision(
    agent_id: str, action: str, decision: str, reason: str
) -> None:
    """Auto-audit every governance evaluation."""
    result = AuditResult.SUCCESS if decision == "allow" else AuditResult.DENIED
    await _get_store().append_audit_record(
        AuditRecordCreate(
            agent_id=agent_id,
            action=f"governance.evaluate:{action}",
            result=result,
            detail=f"Decision: {decision}. {reason}",
            severity=AuditSeverity.INFO if decision == "allow" else AuditSeverity.WARNING,
        ),
        settings.default_tenant,
    )
