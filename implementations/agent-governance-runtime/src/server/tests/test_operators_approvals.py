"""Tests for Operator RBAC and Approval Flows."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_AGENT = {
    "id": "approval-test-agent",
    "name": "Approval Test Agent",
    "platform": "custom",
    "owner": {"team": "eng", "contact": "eng@example.com"},
    "access_profile": {
        "actions": {"file.read": "allow", "deploy.production": "require_approval"},
    },
}


async def _bootstrap_admin(client: AsyncClient) -> str:
    """Create the first operator (bootstrap — no auth needed). Returns api_key."""
    resp = await client.post("/operators", json={
        "name": "Admin User", "email": "admin@company.com", "role": "admin",
    })
    assert resp.status_code == 201
    key = resp.json()["api_key"]
    assert key.startswith("agr-op_")
    return key


async def _create_approver(client: AsyncClient, admin_key: str) -> str:
    """Create an approver. Returns api_key."""
    resp = await client.post("/operators", json={
        "name": "Approver User", "email": "approver@company.com", "role": "approver",
    }, headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 201
    return resp.json()["api_key"]


async def _setup_active_agent(client: AsyncClient) -> str:
    """Register and activate an agent. Returns token."""
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    token = resp.json()["api_token"]
    await client.put("/registry/agents/approval-test-agent", json={"status": "active"})
    return token


# --- Operator Tests ---

@pytest.mark.asyncio
async def test_bootstrap_first_operator(client: AsyncClient):
    """First operator can be created without auth."""
    key = await _bootstrap_admin(client)
    assert key is not None


@pytest.mark.asyncio
async def test_second_operator_requires_admin(client: AsyncClient):
    """Subsequent operators require admin auth."""
    # Bootstrap the first operator (admin)
    admin_key = await _bootstrap_admin(client)

    # Now try creating another without auth — should fail (there's already an operator)
    resp = await client.post("/operators", json={
        "name": "Second", "email": "second@company.com", "role": "approver",
    })
    assert resp.status_code == 401

    # With admin auth — should work
    resp = await client.post("/operators", json={
        "name": "Third", "email": "third@company.com", "role": "approver",
    }, headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_operators_admin_only(client: AsyncClient):
    """Only admins can list operators."""
    admin_key = await _bootstrap_admin(client)
    approver_key = await _create_approver(client, admin_key)

    # Admin can list
    resp = await client.get("/operators", headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

    # Approver cannot list
    resp = await client.get("/operators", headers={"X-Operator-Key": approver_key})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_operator_key_shown_once(client: AsyncClient):
    """api_key should only be in POST response, not GET."""
    admin_key = await _bootstrap_admin(client)
    resp = await client.get("/operators", headers={"X-Operator-Key": admin_key})
    for op in resp.json()["items"]:
        assert "api_key" not in op


# --- Approval Tests ---

@pytest.mark.asyncio
async def test_create_approval_request(client: AsyncClient):
    """Create an approval request."""
    await _setup_active_agent(client)
    resp = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent",
        "action": "deploy.production",
        "reason": "Need to deploy hotfix",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["id"].startswith("apr-")


@pytest.mark.asyncio
async def test_approval_idempotent(client: AsyncClient):
    """Same agent+action should return the same pending approval."""
    await _setup_active_agent(client)
    r1 = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    r2 = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_approve_and_check(client: AsyncClient):
    """Approver can approve a request."""
    admin_key = await _bootstrap_admin(client)
    approver_key = await _create_approver(client, admin_key)
    await _setup_active_agent(client)

    # Create request
    resp = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    approval_id = resp.json()["id"]

    # Approve
    resp = await client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved", "reason": "Looks safe"},
        headers={"X-Operator-Key": approver_key},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["decided_by"] is not None


@pytest.mark.asyncio
async def test_deny_approval(client: AsyncClient):
    admin_key = await _bootstrap_admin(client)
    approver_key = await _create_approver(client, admin_key)
    await _setup_active_agent(client)

    resp = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    approval_id = resp.json()["id"]

    resp = await client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "denied", "reason": "Too risky"},
        headers={"X-Operator-Key": approver_key},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "denied"


@pytest.mark.asyncio
async def test_cannot_decide_twice(client: AsyncClient):
    admin_key = await _bootstrap_admin(client)
    approver_key = await _create_approver(client, admin_key)
    await _setup_active_agent(client)

    resp = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    approval_id = resp.json()["id"]

    await client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved"},
        headers={"X-Operator-Key": approver_key},
    )

    # Second decide should fail
    resp = await client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "denied"},
        headers={"X-Operator-Key": approver_key},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_pending_requires_role(client: AsyncClient):
    """List pending requires approver or admin role."""
    resp = await client.get("/approvals/pending")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_approval_consumed_in_evaluate(client: AsyncClient):
    """Approved request should be consumed during governance evaluate."""
    admin_key = await _bootstrap_admin(client)
    approver_key = await _create_approver(client, admin_key)
    token = await _setup_active_agent(client)

    # 1. Evaluate without approval → require_approval
    resp = await client.post("/governance/evaluate", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    assert resp.json()["decision"] == "require_approval"

    # 2. Create and approve
    resp = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    approval_id = resp.json()["id"]
    await client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved"},
        headers={"X-Operator-Key": approver_key},
    )

    # 3. Evaluate again → should be allowed (approval consumed)
    resp = await client.post("/governance/evaluate", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    assert resp.json()["decision"] == "allow"
    assert "Approved via approval" in resp.json()["reason"]

    # 4. Evaluate a third time → require_approval again (one-time-use)
    resp = await client.post("/governance/evaluate", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    assert resp.json()["decision"] == "require_approval"


@pytest.mark.asyncio
async def test_approval_does_not_bypass_deny(client: AsyncClient):
    """Approval waives require_approval but NOT deny."""
    admin_key = await _bootstrap_admin(client)
    approver_key = await _create_approver(client, admin_key)
    await _setup_active_agent(client)

    # Create a deny policy for deploy.production
    await client.post("/policies/rules", json={
        "name": "No deploys ever",
        "condition": {"action_pattern": "deploy.production"},
        "decision": "deny", "priority": 999,
    })

    # Create and approve an approval request
    resp = await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    approval_id = resp.json()["id"]
    await client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved"},
        headers={"X-Operator-Key": approver_key},
    )

    # Evaluate → should still be DENIED (policy overrides approval)
    resp = await client.post("/governance/evaluate", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    assert resp.json()["decision"] == "deny"


@pytest.mark.asyncio
async def test_approval_audited(client: AsyncClient):
    """Approval creation should generate audit records."""
    await _setup_active_agent(client)
    await client.post("/approvals/request", json={
        "agent_id": "approval-test-agent", "action": "deploy.production",
    })
    resp = await client.get("/audit/records", params={"action": "approval.requested:deploy.production"})
    assert resp.json()["total"] >= 1
