"""Operator Management API — admin users for the governance plane.

Endpoints:
  POST /operators           — Create an operator (admin-only)
  GET  /operators           — List operators (admin-only)
  GET  /operators/{id}      — Get operator (admin-only)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from agr_server.config import settings
from agr_server.models.operator import OperatorCreate, OperatorRecord, OperatorRecordPublic, OperatorList
from agr_server.store.base import Store

router = APIRouter(prefix="/operators", tags=["operators"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set."
    return _store


async def resolve_operator(api_key: str | None) -> dict | None:
    """Resolve operator from X-Operator-Key header. Returns None if not provided."""
    if not api_key:
        return None
    store = _get_store()
    op = await store.get_operator_by_key(api_key)
    if op is None:
        raise HTTPException(status_code=401, detail="Invalid operator key")
    return {"id": op.id, "name": op.name, "role": op.role.value, "tenant_id": op.tenant_id}


async def require_role(api_key: str | None, *roles: str) -> dict:
    """Require operator with one of the specified roles."""
    op = await resolve_operator(api_key)
    if op is None:
        raise HTTPException(status_code=401, detail="X-Operator-Key header required")
    if op["role"] not in roles:
        raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(roles)}")
    return op


@router.post("", response_model=OperatorRecord, status_code=201)
async def create_operator(
    op: OperatorCreate,
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> OperatorRecord:
    """Create a new operator. Returns record WITH api_key (shown once).

    First operator can be created without auth (bootstrap). After that, admin-only.
    """
    store = _get_store()
    existing = await store.list_operators(settings.default_tenant)
    if existing.total > 0:
        await require_role(x_operator_key, "admin")

    try:
        return await store.create_operator(op, settings.default_tenant)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=OperatorList)
async def list_operators(
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> OperatorList:
    """List operators (admin-only, keys redacted)."""
    await require_role(x_operator_key, "admin")
    return await _get_store().list_operators(settings.default_tenant)


@router.get("/{op_id}", response_model=OperatorRecordPublic)
async def get_operator(
    op_id: str,
    x_operator_key: Optional[str] = Header(default=None, alias="X-Operator-Key"),
) -> OperatorRecordPublic:
    """Get operator by ID (admin-only, key redacted)."""
    await require_role(x_operator_key, "admin")
    op = await _get_store().get_operator(op_id, settings.default_tenant)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operator '{op_id}' not found")
    return OperatorRecordPublic.from_record(op)
