"""Tests for Dashboard and Compliance Export APIs."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _setup_fleet(client: AsyncClient) -> str:
    """Set up a fleet with agents, audit records, policies. Returns admin key."""
    # Bootstrap admin
    resp = await client.post("/operators", json={
        "name": "Admin", "email": "admin@co.com", "role": "admin",
    })
    admin_key = resp.json()["api_key"]

    # Register agents
    for agent_id, platform, status in [
        ("agent-a", "claude-code", "active"),
        ("agent-b", "n8n", "active"),
        ("agent-c", "custom", "pending_approval"),
    ]:
        await client.post("/registry/agents", json={
            "id": agent_id, "name": f"Agent {agent_id}",
            "platform": platform,
            "owner": {"team": "eng", "contact": "eng@co.com"},
        })
        if status == "active":
            await client.put(f"/registry/agents/{agent_id}", json={"status": "active"})

    # Create policies
    await client.post("/policies/rules", json={
        "name": "No deploys", "condition": {"action_pattern": "deploy.*"}, "decision": "deny",
    })

    # Generate some audit records
    for agent_id in ["agent-a", "agent-b"]:
        await client.post("/audit/records", json={
            "agent_id": agent_id, "action": "file.read", "result": "success",
        })

    # Generate a denied governance evaluation
    await client.post("/governance/evaluate", json={
        "agent_id": "agent-a", "action": "deploy.production",
    })

    # Budget consumption
    await client.post("/budget/consume", json={
        "agent_id": "agent-a", "requests": 5, "tokens_input": 2000, "cost_usd": 0.1,
    })

    return admin_key


# --- Dashboard Tests ---

@pytest.mark.asyncio
async def test_dashboard_summary(client: AsyncClient):
    admin_key = await _setup_fleet(client)
    resp = await client.get("/dashboard/summary", headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_agents"] == 3
    assert "active" in data["agents_by_status"]
    assert data["total_policies"] >= 1


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient):
    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_top_consumers(client: AsyncClient):
    admin_key = await _setup_fleet(client)
    resp = await client.get("/dashboard/top-consumers", headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_violations(client: AsyncClient):
    admin_key = await _setup_fleet(client)
    resp = await client.get("/dashboard/violations", headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # We generated a denied evaluation for deploy.production
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_dashboard_approvals(client: AsyncClient):
    admin_key = await _setup_fleet(client)
    resp = await client.get("/dashboard/approvals", headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_pending" in data


# --- Compliance Export Tests ---

@pytest.mark.asyncio
async def test_compliance_export(client: AsyncClient):
    admin_key = await _setup_fleet(client)
    resp = await client.get("/compliance/export", headers={"X-Operator-Key": admin_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "1.0.0"
    assert data["tenant_id"] == "default"
    assert data["agent_inventory"]["count"] == 3
    assert data["policy_coverage"]["count"] >= 1
    assert data["audit_trail"]["count"] >= 1
    assert data["evidence_completeness"] in ("complete", "partial", "gaps_detected")


@pytest.mark.asyncio
async def test_compliance_export_requires_auth(client: AsyncClient):
    resp = await client.get("/compliance/export")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_compliance_export_auditor_role(client: AsyncClient):
    """Auditors should be able to access compliance exports."""
    resp = await client.post("/operators", json={
        "name": "Admin", "email": "admin@co.com", "role": "admin",
    })
    admin_key = resp.json()["api_key"]

    resp = await client.post("/operators", json={
        "name": "Auditor", "email": "auditor@co.com", "role": "auditor",
    }, headers={"X-Operator-Key": admin_key})
    auditor_key = resp.json()["api_key"]

    resp = await client.get("/compliance/export", headers={"X-Operator-Key": auditor_key})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_compliance_gaps_detected(client: AsyncClient):
    """Report should flag gaps when agents have no access profile."""
    resp = await client.post("/operators", json={
        "name": "Admin", "email": "admin@co.com", "role": "admin",
    })
    admin_key = resp.json()["api_key"]

    # Agent with no access profile
    await client.post("/registry/agents", json={
        "id": "bare-agent", "name": "Bare Agent", "platform": "custom",
        "owner": {"team": "eng", "contact": "eng@co.com"},
    })

    resp = await client.get("/compliance/export", headers={"X-Operator-Key": admin_key})
    data = resp.json()
    assert data["evidence_completeness"] in ("partial", "gaps_detected")
    assert any("no access profile" in g for g in data["gaps"])
