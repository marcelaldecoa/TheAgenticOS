"""Tests for Budget & Quota tracking."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_AGENT = {
    "id": "budget-test-agent",
    "name": "Budget Test Agent",
    "platform": "custom",
    "owner": {"team": "eng", "contact": "eng@example.com"},
    "access_profile": {
        "actions": {"file.read": "allow"},
        "budget": {
            "max_requests_per_hour": 10,
            "max_tokens_per_hour": 5000,
            "max_cost_per_day_usd": 1.00,
        },
    },
}


@pytest.mark.asyncio
async def test_consume_and_status(client: AsyncClient):
    """Record consumption and check status."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)

    # Record some consumption
    resp = await client.post("/budget/consume", json={
        "agent_id": "budget-test-agent",
        "requests": 3,
        "tokens_input": 1000,
        "tokens_output": 500,
        "cost_usd": 0.05,
    })
    assert resp.status_code == 204

    # Check status
    resp = await client.get("/budget/budget-test-agent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "budget-test-agent"
    assert data["status"] == "ok"
    assert data["hourly_usage"]["requests"] == 3
    assert data["hourly_usage"]["tokens_input"] == 1000


@pytest.mark.asyncio
async def test_budget_accumulates(client: AsyncClient):
    """Multiple consumption records should accumulate."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)

    for _ in range(3):
        await client.post("/budget/consume", json={
            "agent_id": "budget-test-agent",
            "requests": 2,
            "tokens_input": 500,
        })

    resp = await client.get("/budget/budget-test-agent")
    data = resp.json()
    assert data["hourly_usage"]["requests"] == 6
    assert data["hourly_usage"]["tokens_input"] == 1500


@pytest.mark.asyncio
async def test_budget_warning_at_80_percent(client: AsyncClient):
    """Status should be 'warning' at 80% of limit."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)

    # 8 of 10 requests = 80%
    await client.post("/budget/consume", json={
        "agent_id": "budget-test-agent",
        "requests": 8,
    })

    resp = await client.get("/budget/budget-test-agent")
    data = resp.json()
    assert data["status"] == "warning"
    assert len(data["warnings"]) > 0


@pytest.mark.asyncio
async def test_budget_exceeded(client: AsyncClient):
    """Status should be 'exceeded' when over limit."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)

    # 11 of 10 requests = exceeded
    await client.post("/budget/consume", json={
        "agent_id": "budget-test-agent",
        "requests": 11,
    })

    resp = await client.get("/budget/budget-test-agent")
    data = resp.json()
    assert data["status"] == "exceeded"
    assert any("exceeded" in w.lower() for w in data["warnings"])


@pytest.mark.asyncio
async def test_budget_no_agent_no_limits(client: AsyncClient):
    """Agent without budget limits should always be 'ok'."""
    resp = await client.get("/budget/unknown-agent")
    data = resp.json()
    assert data["status"] == "ok"
    assert data["hourly_usage"] is None
