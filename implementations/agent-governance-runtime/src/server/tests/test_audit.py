"""Tests for the Audit Trail API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_AUDIT= {
    "agent_id": "test-agent",
    "action": "email.send",
    "result": "success",
    "intent": "Notify customer about ticket resolution",
    "trace_id": "trace-001",
    "span_id": "span-001",
    "capabilities_exercised": ["email.send"],
    "cost": {"tokens_input": 100, "tokens_output": 50, "duration_ms": 500},
}


@pytest.mark.asyncio
async def test_append_audit_record(client: AsyncClient):
    resp = await client.post("/audit/records", json=SAMPLE_AUDIT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent_id"] == "test-agent"
    assert data["action"] == "email.send"
    assert data["sequence"] >= 1
    assert data["timestamp"] is not None
    assert data["tenant_id"] == "default"


@pytest.mark.asyncio
async def test_audit_records_are_sequential(client: AsyncClient):
    r1 = await client.post("/audit/records", json=SAMPLE_AUDIT)
    r2 = await client.post("/audit/records", json=SAMPLE_AUDIT)
    assert r2.json()["sequence"] > r1.json()["sequence"]


@pytest.mark.asyncio
async def test_query_audit_records(client: AsyncClient):
    await client.post("/audit/records", json=SAMPLE_AUDIT)
    resp = await client.get("/audit/records")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_query_audit_by_agent(client: AsyncClient):
    await client.post("/audit/records", json=SAMPLE_AUDIT)
    resp = await client.get("/audit/records", params={"agent_id": "test-agent"})
    data = resp.json()
    assert all(r["agent_id"] == "test-agent" for r in data["items"])


@pytest.mark.asyncio
async def test_query_audit_by_action(client: AsyncClient):
    await client.post("/audit/records", json=SAMPLE_AUDIT)
    await client.post("/audit/records", json={**SAMPLE_AUDIT, "action": "db.query"})
    resp = await client.get("/audit/records", params={"action": "email.send"})
    data = resp.json()
    assert all(r["action"] == "email.send" for r in data["items"])


@pytest.mark.asyncio
async def test_agent_audit_trail(client: AsyncClient):
    await client.post("/audit/records", json=SAMPLE_AUDIT)
    resp = await client.get("/audit/agents/test-agent/records")
    assert resp.status_code == 200
    data = resp.json()
    assert all(r["agent_id"] == "test-agent" for r in data["items"])


@pytest.mark.asyncio
async def test_trace_reconstruction(client: AsyncClient):
    trace_id = "trace-reconstruct-001"
    for i, action in enumerate(["classify", "analyze", "decide", "execute"]):
        await client.post("/audit/records", json={
            "agent_id": f"agent-{action}",
            "action": f"step.{action}",
            "result": "success",
            "trace_id": trace_id,
            "span_id": f"span-{i}",
        })

    resp = await client.get(f"/audit/traces/{trace_id}")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 4
    # Verify ordered by sequence (ascending)
    sequences = [r["sequence"] for r in records]
    assert sequences == sorted(sequences)


@pytest.mark.asyncio
async def test_no_update_endpoint(client: AsyncClient):
    """Audit records must be append-only — no update endpoint should exist."""
    resp = await client.put("/audit/records/1", json={"result": "failure"})
    assert resp.status_code in (404, 405)


@pytest.mark.asyncio
async def test_no_delete_endpoint(client: AsyncClient):
    """Audit records must be append-only — no delete endpoint should exist."""
    resp = await client.delete("/audit/records/1")
    assert resp.status_code in (404, 405)
