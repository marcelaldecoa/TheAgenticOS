"""Tests for the unified Governance Evaluation endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_AGENT = {
    "id": "gov-test-agent",
    "name": "Governance Test Agent",
    "platform": "custom",
    "owner": {"team": "eng", "contact": "eng@example.com"},
    "deployment": {"environment": "production"},
    "access_profile": {
        "mcps_allowed": ["github-mcp"],
        "actions": {
            "file.read": "allow",
            "file.write": "allow",
            "deploy.*": "deny",
            "git.push": "require_approval",
        },
        "budget": {
            "max_requests_per_hour": 100,
        },
    },
}


async def _setup_active_agent(client: AsyncClient) -> str:
    """Register and activate an agent, returning its token."""
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    token = resp.json()["api_token"]
    # Activate the agent
    await client.put("/registry/agents/gov-test-agent", json={"status": "active"})
    return token


@pytest.mark.asyncio
async def test_evaluate_allowed_action(client: AsyncClient):
    """Action with no restrictions should be allowed."""
    await _setup_active_agent(client)

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.read",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "allow"
    assert data["agent_status"] == "active"
    assert data["budget_status"] == "ok"


@pytest.mark.asyncio
async def test_evaluate_denied_by_profile(client: AsyncClient):
    """Action denied by access profile should return deny."""
    await _setup_active_agent(client)

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "deploy.production",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "deny"
    assert "Access profile" in data["reason"]


@pytest.mark.asyncio
async def test_evaluate_require_approval(client: AsyncClient):
    """Action requiring approval should return require_approval."""
    await _setup_active_agent(client)

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "git.push",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "require_approval"


@pytest.mark.asyncio
async def test_evaluate_inactive_agent_denied(client: AsyncClient):
    """Inactive agents should always be denied."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    # Agent is pending_approval, not active

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.read",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"
    assert "pending_approval" in resp.json()["reason"]


@pytest.mark.asyncio
async def test_evaluate_unknown_agent(client: AsyncClient):
    """Unknown agent should return 404."""
    resp = await client.post("/governance/evaluate", json={
        "agent_id": "nonexistent",
        "action": "file.read",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_with_token(client: AsyncClient):
    """Token-based auth should override the body's agent_id."""
    token = await _setup_active_agent(client)

    resp = await client.post(
        "/governance/evaluate",
        json={
            "agent_id": "wrong-agent",
            "action": "file.read",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


@pytest.mark.asyncio
async def test_evaluate_policy_overrides_profile(client: AsyncClient):
    """Tenant policy should deny even if access profile allows."""
    await _setup_active_agent(client)

    # Create a policy that denies file.write for all agents
    await client.post("/policies/rules", json={
        "name": "No file writes",
        "condition": {"action_pattern": "file.write"},
        "decision": "deny",
        "priority": 200,
    })

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.write",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"
    assert "No file writes" in resp.json()["reason"]


@pytest.mark.asyncio
async def test_evaluate_policy_wildcard_match(client: AsyncClient):
    """Wildcard policy should match child actions."""
    await _setup_active_agent(client)

    await client.post("/policies/rules", json={
        "name": "All database ops need approval",
        "condition": {"action_pattern": "database.*"},
        "decision": "require_approval",
        "priority": 100,
    })

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "database.write",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "require_approval"


@pytest.mark.asyncio
async def test_evaluate_deny_beats_require_approval(client: AsyncClient):
    """When both deny and require_approval match, deny wins."""
    await _setup_active_agent(client)

    await client.post("/policies/rules", json={
        "name": "Email needs approval",
        "condition": {"action_pattern": "email.*"},
        "decision": "require_approval",
        "priority": 100,
    })
    await client.post("/policies/rules", json={
        "name": "No sending to external",
        "condition": {"action_pattern": "email.send"},
        "decision": "deny",
        "priority": 200,
    })

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "email.send",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


@pytest.mark.asyncio
async def test_evaluate_disabled_policy_ignored(client: AsyncClient):
    """Disabled policies should not affect evaluation."""
    await _setup_active_agent(client)

    resp = await client.post("/policies/rules", json={
        "name": "No file reads (disabled)",
        "condition": {"action_pattern": "file.read"},
        "decision": "deny",
        "priority": 999,
    })
    policy_id = resp.json()["id"]
    await client.patch(f"/policies/rules/{policy_id}", json={"enabled": False})

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.read",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


@pytest.mark.asyncio
async def test_evaluate_auto_audits(client: AsyncClient):
    """Governance evaluations should create audit records."""
    await _setup_active_agent(client)

    await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.read",
    })

    resp = await client.get("/audit/records", params={"action": "governance.evaluate:file.read"})
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_evaluate_budget_exceeded_denies(client: AsyncClient):
    """When request budget is exceeded, action should be denied."""
    await _setup_active_agent(client)

    # Exhaust the budget (max 100 requests/hour)
    await client.post("/budget/consume", json={
        "agent_id": "gov-test-agent",
        "requests": 101,
    })

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.read",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"
    assert resp.json()["budget_status"] == "exceeded"


@pytest.mark.asyncio
async def test_evaluate_policy_platform_filter(client: AsyncClient):
    """Policy with platform filter should only match the specified platform."""
    await _setup_active_agent(client)

    # Policy that only applies to n8n agents
    await client.post("/policies/rules", json={
        "name": "N8N: no deploys",
        "condition": {
            "action_pattern": "file.write",
            "platforms": ["n8n"],
        },
        "decision": "deny",
        "priority": 200,
    })

    # Our agent is 'custom', not 'n8n' — should NOT be affected
    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "file.write",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


@pytest.mark.asyncio
async def test_evaluate_matched_rules_returned(client: AsyncClient):
    """Response should include which policies matched."""
    await _setup_active_agent(client)

    await client.post("/policies/rules", json={
        "name": "Approve all writes",
        "condition": {"action_pattern": "*.write"},
        "decision": "require_approval",
        "priority": 50,
    })

    resp = await client.post("/governance/evaluate", json={
        "agent_id": "gov-test-agent",
        "action": "database.write",
    })
    data = resp.json()
    assert data["decision"] == "require_approval"
    assert len(data["matched_rules"]) >= 1
    assert data["matched_rules"][0]["policy_name"] == "Approve all writes"
