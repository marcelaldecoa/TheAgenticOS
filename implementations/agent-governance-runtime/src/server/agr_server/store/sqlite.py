"""SQLite storage backend.

Uses aiosqlite for async I/O. Data is stored as JSON blobs for flexibility
during Phase 1 — structured columns for indexed fields, JSON for the rest.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from agr_server.models.agent import (
    AgentCreate,
    AgentList,
    AgentRecord,
    AgentStatus,
    AgentUpdate,
)
from agr_server.models.audit import (
    AuditQuery,
    AuditRecord,
    AuditRecordCreate,
    AuditRecordList,
)
from agr_server.store.base import Store


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_token() -> str:
    """Generate a secure API token for agent authentication."""
    return f"agr_{secrets.token_urlsafe(32)}"


class SQLiteStore(Store):
    """SQLite-backed store for the Agent Governance Runtime."""

    def __init__(self, db_path: str | Path = "agr.db") -> None:
        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id          TEXT NOT NULL,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                name        TEXT NOT NULL,
                platform    TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending_approval',
                owner_team  TEXT NOT NULL,
                environment TEXT,
                api_token   TEXT,
                data        TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                updated_at    TEXT NOT NULL,
                PRIMARY KEY (tenant_id, id)
            );

            CREATE INDEX IF NOT EXISTS idx_agents_platform
                ON agents(tenant_id, platform);
            CREATE INDEX IF NOT EXISTS idx_agents_status
                ON agents(tenant_id, status);
            CREATE INDEX IF NOT EXISTS idx_agents_owner
                ON agents(tenant_id, owner_team);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_token
                ON agents(api_token);

            CREATE TABLE IF NOT EXISTS audit_records (
                sequence    INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                timestamp   TEXT NOT NULL,
                agent_id    TEXT NOT NULL,
                action      TEXT NOT NULL,
                result      TEXT NOT NULL,
                severity    TEXT NOT NULL DEFAULT 'info',
                trace_id    TEXT,
                run_id      TEXT,
                session_id  TEXT,
                data        TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_audit_agent
                ON audit_records(tenant_id, agent_id);
            CREATE INDEX IF NOT EXISTS idx_audit_trace
                ON audit_records(tenant_id, trace_id);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_records(tenant_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_action
                ON audit_records(tenant_id, action);
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Store not initialized. Call initialize() first."
        return self._db

    # --- Agent Registry ---

    async def register_agent(self, agent: AgentCreate, tenant_id: str) -> AgentRecord:
        now = _now()
        token = _generate_token()
        record = AgentRecord(
            **agent.model_dump(),
            status=AgentStatus.PENDING_APPROVAL,
            tenant_id=tenant_id,
            api_token=token,
            registered_at=now,
            updated_at=now,
            first_seen_at=now,
        )
        env = record.deployment.environment if record.deployment else None
        try:
            await self.db.execute(
                """INSERT INTO agents
                   (id, tenant_id, name, platform, status,
                    owner_team, environment, api_token, data,
                    registered_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    tenant_id,
                    record.name,
                    record.platform,
                    record.status.value,
                    record.owner.team,
                    env,
                    token,
                    record.model_dump_json(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            await self.db.commit()
        except aiosqlite.IntegrityError:
            raise ValueError(f"Agent '{agent.id}' already exists in tenant '{tenant_id}'")
        return record

    async def get_agent(self, agent_id: str, tenant_id: str) -> AgentRecord | None:
        cursor = await self.db.execute(
            "SELECT data FROM agents WHERE id = ? AND tenant_id = ?",
            (agent_id, tenant_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return AgentRecord.model_validate_json(row["data"])

    async def get_agent_by_token(self, token: str) -> AgentRecord | None:
        """Look up an agent by its API token. Used for MCP authentication."""
        cursor = await self.db.execute(
            "SELECT data FROM agents WHERE api_token = ?", (token,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return AgentRecord.model_validate_json(row["data"])

    async def update_agent(
        self, agent_id: str, update: AgentUpdate, tenant_id: str
    ) -> AgentRecord | None:
        existing = await self.get_agent(agent_id, tenant_id)
        if existing is None:
            return None

        now = _now()
        update_data = update.model_dump(exclude_none=True)
        merged = existing.model_dump()
        merged.update(update_data)
        merged["updated_at"] = now

        record = AgentRecord.model_validate(merged)
        env = record.deployment.environment if record.deployment else None
        await self.db.execute(
            """UPDATE agents SET
               name = ?, platform = ?, status = ?,
               owner_team = ?, environment = ?, data = ?, updated_at = ?
               WHERE id = ? AND tenant_id = ?""",
            (
                record.name,
                record.platform,
                record.status.value,
                record.owner.team,
                env,
                record.model_dump_json(),
                now.isoformat(),
                agent_id,
                tenant_id,
            ),
        )
        await self.db.commit()
        return record

    async def deprecate_agent(self, agent_id: str, tenant_id: str) -> bool:
        update = AgentUpdate(status=AgentStatus.DEPRECATED)
        result = await self.update_agent(agent_id, update, tenant_id)
        return result is not None

    async def list_agents(
        self,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        platform: str | None = None,
        status: str | None = None,
        owner_team: str | None = None,
        search: str | None = None,
    ) -> AgentList:
        conditions = ["tenant_id = ?"]
        params: list[str | int] = [tenant_id]

        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if owner_team:
            conditions.append("owner_team = ?")
            params.append(owner_team)
        if search:
            conditions.append("(name LIKE ? OR id LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = " AND ".join(conditions)

        cursor = await self.db.execute(
            f"SELECT COUNT(*) as cnt FROM agents WHERE {where}", params
        )
        row = await cursor.fetchone()
        total = row["cnt"]

        offset = (page - 1) * page_size
        cursor = await self.db.execute(
            f"""SELECT data FROM agents WHERE {where}
                ORDER BY registered_at DESC LIMIT ? OFFSET ?""",
            [*params, page_size, offset],
        )
        rows = await cursor.fetchall()
        items = [AgentRecord.model_validate_json(r["data"]) for r in rows]

        return AgentList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    # --- Audit Trail (append-only — no update, no delete) ---

    async def append_audit_record(
        self, record: AuditRecordCreate, tenant_id: str
    ) -> AuditRecord:
        now = _now()
        # Insert first to get the server-assigned sequence
        cursor = await self.db.execute(
            """INSERT INTO audit_records
               (tenant_id, timestamp, agent_id, action, result, severity,
                trace_id, run_id, session_id, data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                now.isoformat(),
                record.agent_id,
                record.action,
                record.result.value,
                record.severity.value,
                record.trace_id,
                record.run_id,
                record.session_id,
                "{}",  # placeholder
            ),
        )
        sequence = cursor.lastrowid
        assert sequence is not None

        audit_record = AuditRecord(
            sequence=sequence,
            timestamp=now,
            tenant_id=tenant_id,
            **record.model_dump(),
        )

        # Update with full JSON data
        await self.db.execute(
            "UPDATE audit_records SET data = ? WHERE sequence = ?",
            (audit_record.model_dump_json(), sequence),
        )
        await self.db.commit()
        return audit_record

    async def query_audit_records(
        self, query: AuditQuery, tenant_id: str
    ) -> AuditRecordList:
        conditions = ["tenant_id = ?"]
        params: list[str | int] = [tenant_id]

        if query.agent_id:
            conditions.append("agent_id = ?")
            params.append(query.agent_id)
        if query.action:
            conditions.append("action = ?")
            params.append(query.action)
        if query.result:
            conditions.append("result = ?")
            params.append(query.result.value)
        if query.severity:
            conditions.append("severity = ?")
            params.append(query.severity.value)
        if query.trace_id:
            conditions.append("trace_id = ?")
            params.append(query.trace_id)
        if query.run_id:
            conditions.append("run_id = ?")
            params.append(query.run_id)
        if query.session_id:
            conditions.append("session_id = ?")
            params.append(query.session_id)
        if query.since:
            conditions.append("timestamp >= ?")
            params.append(query.since.isoformat())
        if query.until:
            conditions.append("timestamp <= ?")
            params.append(query.until.isoformat())

        where = " AND ".join(conditions)

        cursor = await self.db.execute(
            f"SELECT COUNT(*) as cnt FROM audit_records WHERE {where}", params
        )
        row = await cursor.fetchone()
        total = row["cnt"]

        offset = (query.page - 1) * query.page_size
        cursor = await self.db.execute(
            f"""SELECT data FROM audit_records WHERE {where}
                ORDER BY sequence DESC LIMIT ? OFFSET ?""",
            [*params, query.page_size, offset],
        )
        rows = await cursor.fetchall()
        items = [AuditRecord.model_validate_json(r["data"]) for r in rows]

        return AuditRecordList(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            has_more=(offset + query.page_size) < total,
        )

    async def get_agent_audit_trail(
        self,
        agent_id: str,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> AuditRecordList:
        query = AuditQuery(agent_id=agent_id, page=page, page_size=page_size)
        return await self.query_audit_records(query, tenant_id)

    async def get_trace(self, trace_id: str, tenant_id: str) -> list[AuditRecord]:
        cursor = await self.db.execute(
            """SELECT data FROM audit_records
               WHERE tenant_id = ? AND trace_id = ?
               ORDER BY sequence ASC""",
            (tenant_id, trace_id),
        )
        rows = await cursor.fetchall()
        return [AuditRecord.model_validate_json(r["data"]) for r in rows]
