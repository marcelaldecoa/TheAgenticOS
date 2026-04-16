"""Shared test fixtures."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from agr_server.api import audit as audit_api
from agr_server.api import registry as registry_api
from agr_server.main import app
from agr_server.store.sqlite import SQLiteStore


@pytest.fixture(autouse=True)
async def _setup_store(tmp_path):
    """Initialize a fresh in-memory SQLite store for each test."""
    store = SQLiteStore(db_path=":memory:")
    await store.initialize()
    registry_api.set_store(store)
    audit_api.set_store(store)
    yield
    await store.close()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
