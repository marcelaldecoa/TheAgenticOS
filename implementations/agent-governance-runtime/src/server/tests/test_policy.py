"""Tests for the Policy Engine API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_POLICY = {
    "name": "No production deployments",
    "description": "Block all deployment actions to production",
    "condition": {
        "action_pattern": "deploy.production",
    },
    "decision": "deny",
    "priority": 200,
}

SAMPLE_WILDCARD_POLICY = {
    "name": "All deploys need approval",
    "condition": {
        "action_pattern": "deploy.*",
    },
    "decision": "require_approval",
    "priority": 100,
}


@pytest.mark.asyncio
async def test_create_policy(client: AsyncClient):
    resp = await client.post("/policies/rules", json=SAMPLE_POLICY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "No production deployments"
    assert data["decision"] == "deny"
    assert data["enabled"] is True
    assert data["id"].startswith("pol-")


@pytest.mark.asyncio
async def test_get_policy(client: AsyncClient):
    resp = await client.post("/policies/rules", json=SAMPLE_POLICY)
    policy_id = resp.json()["id"]

    resp = await client.get(f"/policies/rules/{policy_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "No production deployments"


@pytest.mark.asyncio
async def test_get_policy_not_found(client: AsyncClient):
    resp = await client.get("/policies/rules/pol-nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_policies(client: AsyncClient):
    await client.post("/policies/rules", json=SAMPLE_POLICY)
    await client.post("/policies/rules", json=SAMPLE_WILDCARD_POLICY)

    resp = await client.get("/policies/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_policies_enabled_only(client: AsyncClient):
    resp1 = await client.post("/policies/rules", json=SAMPLE_POLICY)
    await client.post("/policies/rules", json=SAMPLE_WILDCARD_POLICY)

    # Disable one
    policy_id = resp1.json()["id"]
    await client.patch(f"/policies/rules/{policy_id}", json={"enabled": False})

    resp = await client.get("/policies/rules", params={"enabled_only": True})
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_disable_policy(client: AsyncClient):
    resp = await client.post("/policies/rules", json=SAMPLE_POLICY)
    policy_id = resp.json()["id"]

    resp = await client.patch(f"/policies/rules/{policy_id}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_update_policy_priority(client: AsyncClient):
    resp = await client.post("/policies/rules", json=SAMPLE_POLICY)
    policy_id = resp.json()["id"]

    resp = await client.patch(f"/policies/rules/{policy_id}", json={"priority": 500})
    assert resp.status_code == 200
    assert resp.json()["priority"] == 500


@pytest.mark.asyncio
async def test_policy_creation_audited(client: AsyncClient):
    """Creating a policy should create an audit record."""
    await client.post("/policies/rules", json=SAMPLE_POLICY)

    resp = await client.get("/audit/records", params={"action": "policy.created"})
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["agent_id"] == "system:policy-engine"


@pytest.mark.asyncio
async def test_policy_disable_audited(client: AsyncClient):
    """Disabling a policy should create an audit record."""
    resp = await client.post("/policies/rules", json=SAMPLE_POLICY)
    policy_id = resp.json()["id"]

    await client.patch(f"/policies/rules/{policy_id}", json={"enabled": False})

    resp = await client.get("/audit/records", params={"action": "policy.disabled"})
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_no_hard_delete(client: AsyncClient):
    """Policy DELETE endpoint should not exist."""
    resp = await client.post("/policies/rules", json=SAMPLE_POLICY)
    policy_id = resp.json()["id"]

    resp = await client.delete(f"/policies/rules/{policy_id}")
    assert resp.status_code in (404, 405)
