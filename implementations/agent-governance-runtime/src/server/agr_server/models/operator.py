"""Operator (admin/human) models — RBAC for governance operations.

Operators are human users who manage the governance plane:
- **admin**: Full access — create operators, manage policies, view everything
- **approver**: Decide on approval requests, view dashboard
- **auditor**: Read-only access to audit trail, dashboard, compliance exports
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OperatorRole(StrEnum):
    """Role-based access control for operators."""

    ADMIN = "admin"
    APPROVER = "approver"
    AUDITOR = "auditor"


class OperatorCreate(BaseModel):
    """Request body for creating an operator."""

    name: str = Field(min_length=1, max_length=256)
    email: str = Field(min_length=1, max_length=256)
    role: OperatorRole = OperatorRole.APPROVER


class OperatorRecord(BaseModel):
    """Full operator record. api_key shown only on creation."""

    id: str
    name: str
    email: str
    role: OperatorRole
    tenant_id: str = "default"
    api_key: str | None = Field(default=None, description="Shown once on creation")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OperatorRecordPublic(BaseModel):
    """Operator record without api_key (for GET/LIST)."""

    id: str
    name: str
    email: str
    role: OperatorRole
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_record(cls, record: OperatorRecord) -> OperatorRecordPublic:
        return cls.model_validate(record.model_dump(exclude={"api_key"}))


class OperatorList(BaseModel):
    """Paginated list of operators (keys redacted)."""

    items: list[OperatorRecordPublic]
    total: int
