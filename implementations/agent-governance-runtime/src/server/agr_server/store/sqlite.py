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
    AgentRecordPublic,
    AgentStatus,
    AgentUpdate,
)
from agr_server.models.audit import (
    AuditQuery,
    AuditRecord,
    AuditRecordCreate,
    AuditRecordList,
)
from agr_server.models.policy import PolicyCondition, PolicyRule, PolicyRuleCreate, PolicyRuleList, PolicyRuleUpdate
from agr_server.models.budget import BudgetConsumeRequest, BudgetPeriodUsage, BudgetStatus
from agr_server.models.operator import OperatorCreate, OperatorRecord, OperatorRecordPublic, OperatorList
from agr_server.models.approval import ApprovalRecord, ApprovalRequestCreate, ApprovalList, ApprovalStatus, ApprovalDecision
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

            CREATE TABLE IF NOT EXISTS policies (
                id          TEXT PRIMARY KEY,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                name        TEXT NOT NULL,
                action_pattern TEXT NOT NULL,
                decision    TEXT NOT NULL,
                priority    INTEGER NOT NULL DEFAULT 100,
                enabled     INTEGER NOT NULL DEFAULT 1,
                data        TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_policies_tenant
                ON policies(tenant_id, enabled);
            CREATE INDEX IF NOT EXISTS idx_policies_pattern
                ON policies(tenant_id, action_pattern);

            CREATE TABLE IF NOT EXISTS budget_consumption (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                agent_id    TEXT NOT NULL,
                period_key  TEXT NOT NULL,
                period_type TEXT NOT NULL DEFAULT 'hourly',
                requests    INTEGER NOT NULL DEFAULT 0,
                tokens_input  INTEGER NOT NULL DEFAULT 0,
                tokens_output INTEGER NOT NULL DEFAULT 0,
                cost_usd    REAL NOT NULL DEFAULT 0.0,
                updated_at  TEXT NOT NULL,
                UNIQUE(tenant_id, agent_id, period_key, period_type)
            );

            CREATE INDEX IF NOT EXISTS idx_budget_agent
                ON budget_consumption(tenant_id, agent_id, period_type, period_key);

            CREATE TABLE IF NOT EXISTS operators (
                id          TEXT PRIMARY KEY,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                name        TEXT NOT NULL,
                email       TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'approver',
                api_key     TEXT,
                data        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_operators_key
                ON operators(api_key);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_operators_email
                ON operators(tenant_id, email);

            CREATE TABLE IF NOT EXISTS approvals (
                id          TEXT PRIMARY KEY,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                agent_id    TEXT NOT NULL,
                action      TEXT NOT NULL,
                context_hash TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                decided_by  TEXT,
                decided_at  TEXT,
                expires_at  TEXT NOT NULL,
                consumed_at TEXT,
                data        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_approvals_pending
                ON approvals(tenant_id, status, expires_at);
            CREATE INDEX IF NOT EXISTS idx_approvals_hash
                ON approvals(tenant_id, context_hash, status);
            CREATE INDEX IF NOT EXISTS idx_approvals_agent
                ON approvals(tenant_id, agent_id, status);
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
        items = [
            AgentRecordPublic.from_record(AgentRecord.model_validate_json(r["data"]))
            for r in rows
        ]

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

    # --- Policy Engine ---

    async def create_policy(self, rule: PolicyRuleCreate, tenant_id: str) -> PolicyRule:
        """Create a new policy rule. Returns the created rule with server-assigned ID."""
        import uuid

        now = _now()
        rule_id = f"pol-{uuid.uuid4().hex[:12]}"
        record = PolicyRule(
            id=rule_id,
            tenant_id=tenant_id,
            name=rule.name,
            description=rule.description,
            condition=rule.condition,
            decision=rule.decision,
            priority=rule.priority,
            enabled=True,
            tags=rule.tags,
            metadata=rule.metadata,
            created_at=now,
            updated_at=now,
        )
        await self.db.execute(
            """INSERT INTO policies
               (id, tenant_id, name, action_pattern, decision, priority, enabled,
                data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rule_id,
                tenant_id,
                record.name,
                record.condition.action_pattern,
                record.decision.value,
                record.priority,
                1,
                record.model_dump_json(),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await self.db.commit()
        return record

    async def get_policy(self, policy_id: str, tenant_id: str) -> PolicyRule | None:
        cursor = await self.db.execute(
            "SELECT data FROM policies WHERE id = ? AND tenant_id = ?",
            (policy_id, tenant_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return PolicyRule.model_validate_json(row["data"])

    async def update_policy(
        self, policy_id: str, update: PolicyRuleUpdate, tenant_id: str
    ) -> PolicyRule | None:
        existing = await self.get_policy(policy_id, tenant_id)
        if existing is None:
            return None

        now = _now()
        update_data = update.model_dump(exclude_none=True)
        merged = existing.model_dump()
        merged.update(update_data)
        merged["updated_at"] = now

        record = PolicyRule.model_validate(merged)
        await self.db.execute(
            """UPDATE policies SET
               name = ?, decision = ?, priority = ?, enabled = ?,
               data = ?, updated_at = ?
               WHERE id = ? AND tenant_id = ?""",
            (
                record.name,
                record.decision.value,
                record.priority,
                1 if record.enabled else 0,
                record.model_dump_json(),
                now.isoformat(),
                policy_id,
                tenant_id,
            ),
        )
        await self.db.commit()
        return record

    async def list_policies(
        self,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        enabled_only: bool = False,
    ) -> PolicyRuleList:
        conditions = ["tenant_id = ?"]
        params: list[str | int] = [tenant_id]
        if enabled_only:
            conditions.append("enabled = 1")

        where = " AND ".join(conditions)

        cursor = await self.db.execute(
            f"SELECT COUNT(*) as cnt FROM policies WHERE {where}", params
        )
        row = await cursor.fetchone()
        total = row["cnt"]

        offset = (page - 1) * page_size
        cursor = await self.db.execute(
            f"""SELECT data FROM policies WHERE {where}
                ORDER BY priority DESC, created_at DESC LIMIT ? OFFSET ?""",
            [*params, page_size, offset],
        )
        rows = await cursor.fetchall()
        items = [PolicyRule.model_validate_json(r["data"]) for r in rows]

        return PolicyRuleList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def get_enabled_policies(self, tenant_id: str) -> list[PolicyRule]:
        """Get all enabled policies for evaluation. No pagination — policies should be manageable."""
        cursor = await self.db.execute(
            "SELECT data FROM policies WHERE tenant_id = ? AND enabled = 1 ORDER BY priority DESC",
            (tenant_id,),
        )
        rows = await cursor.fetchall()
        return [PolicyRule.model_validate_json(r["data"]) for r in rows]

    # --- Budget Tracking ---

    async def record_consumption(
        self, request: BudgetConsumeRequest, tenant_id: str
    ) -> None:
        """Record resource consumption. Upserts into period buckets."""
        now = _now()
        hourly_key = now.strftime("%Y-%m-%dT%H")
        daily_key = now.strftime("%Y-%m-%d")

        for period_key, period_type in [(hourly_key, "hourly"), (daily_key, "daily")]:
            await self.db.execute(
                """INSERT INTO budget_consumption
                   (tenant_id, agent_id, period_key, period_type,
                    requests, tokens_input, tokens_output, cost_usd, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(tenant_id, agent_id, period_key, period_type)
                   DO UPDATE SET
                     requests = requests + excluded.requests,
                     tokens_input = tokens_input + excluded.tokens_input,
                     tokens_output = tokens_output + excluded.tokens_output,
                     cost_usd = cost_usd + excluded.cost_usd,
                     updated_at = excluded.updated_at""",
                (
                    tenant_id,
                    request.agent_id,
                    period_key,
                    period_type,
                    request.requests,
                    request.tokens_input,
                    request.tokens_output,
                    request.cost_usd,
                    now.isoformat(),
                ),
            )
        await self.db.commit()

    async def get_budget_status(
        self, agent_id: str, tenant_id: str
    ) -> BudgetStatus:
        """Get current budget status for an agent."""
        now = _now()
        hourly_key = now.strftime("%Y-%m-%dT%H")
        daily_key = now.strftime("%Y-%m-%d")

        # Get hourly usage
        cursor = await self.db.execute(
            """SELECT requests, tokens_input, tokens_output, cost_usd
               FROM budget_consumption
               WHERE tenant_id = ? AND agent_id = ? AND period_key = ? AND period_type = 'hourly'""",
            (tenant_id, agent_id, hourly_key),
        )
        hourly_row = await cursor.fetchone()
        hourly_usage = None
        if hourly_row:
            hourly_usage = BudgetPeriodUsage(
                period=hourly_key,
                requests=hourly_row["requests"],
                tokens_input=hourly_row["tokens_input"],
                tokens_output=hourly_row["tokens_output"],
                cost_usd=hourly_row["cost_usd"],
            )

        # Get daily usage
        cursor = await self.db.execute(
            """SELECT requests, tokens_input, tokens_output, cost_usd
               FROM budget_consumption
               WHERE tenant_id = ? AND agent_id = ? AND period_key = ? AND period_type = 'daily'""",
            (tenant_id, agent_id, daily_key),
        )
        daily_row = await cursor.fetchone()
        daily_usage = None
        if daily_row:
            daily_usage = BudgetPeriodUsage(
                period=daily_key,
                requests=daily_row["requests"],
                tokens_input=daily_row["tokens_input"],
                tokens_output=daily_row["tokens_output"],
                cost_usd=daily_row["cost_usd"],
            )

        # Get agent's budget limits
        agent = await self.get_agent(agent_id, tenant_id)
        limits = {}
        if agent and agent.access_profile.budget:
            budget = agent.access_profile.budget
            limits = {
                "max_requests_per_hour": budget.max_requests_per_hour,
                "max_tokens_per_hour": budget.max_tokens_per_hour,
                "max_cost_per_day_usd": budget.max_cost_per_day_usd,
            }

        status = BudgetStatus(
            agent_id=agent_id,
            hourly_usage=hourly_usage,
            daily_usage=daily_usage,
            **limits,
        )
        status.compute_status()
        return status

    # --- Operators ---

    async def create_operator(self, op: OperatorCreate, tenant_id: str) -> OperatorRecord:
        import uuid
        now = _now()
        op_id = f"op-{uuid.uuid4().hex[:12]}"
        api_key = f"agr-op_{secrets.token_urlsafe(32)}"
        record = OperatorRecord(
            id=op_id,
            name=op.name,
            email=op.email,
            role=op.role,
            tenant_id=tenant_id,
            api_key=api_key,
            created_at=now,
        )
        try:
            await self.db.execute(
                """INSERT INTO operators (id, tenant_id, name, email, role, api_key, data, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (op_id, tenant_id, record.name, record.email, record.role.value,
                 api_key, record.model_dump_json(), now.isoformat()),
            )
            await self.db.commit()
        except aiosqlite.IntegrityError:
            raise ValueError(f"Operator with email '{op.email}' already exists")
        return record

    async def get_operator(self, op_id: str, tenant_id: str) -> OperatorRecord | None:
        cursor = await self.db.execute(
            "SELECT data FROM operators WHERE id = ? AND tenant_id = ?", (op_id, tenant_id)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return OperatorRecord.model_validate_json(row["data"])

    async def get_operator_by_key(self, api_key: str) -> OperatorRecord | None:
        cursor = await self.db.execute(
            "SELECT data FROM operators WHERE api_key = ?", (api_key,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return OperatorRecord.model_validate_json(row["data"])

    async def list_operators(self, tenant_id: str) -> OperatorList:
        cursor = await self.db.execute(
            "SELECT data FROM operators WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,)
        )
        rows = await cursor.fetchall()
        items = [OperatorRecordPublic.from_record(OperatorRecord.model_validate_json(r["data"])) for r in rows]
        return OperatorList(items=items, total=len(items))

    # --- Approvals ---

    async def create_approval(
        self, req: ApprovalRequestCreate, tenant_id: str, expires_at: datetime
    ) -> ApprovalRecord:
        import uuid
        now = _now()
        context_hash = req.compute_context_hash()

        # Idempotent: return existing pending approval for same context
        cursor = await self.db.execute(
            """SELECT data FROM approvals
               WHERE tenant_id = ? AND context_hash = ? AND status = 'pending' AND expires_at > ?""",
            (tenant_id, context_hash, now.isoformat()),
        )
        existing = await cursor.fetchone()
        if existing:
            return ApprovalRecord.model_validate_json(existing["data"])

        approval_id = f"apr-{uuid.uuid4().hex[:12]}"
        record = ApprovalRecord(
            id=approval_id,
            tenant_id=tenant_id,
            agent_id=req.agent_id,
            action=req.action,
            resource=req.resource,
            context=req.context,
            context_hash=context_hash,
            status=ApprovalStatus.PENDING,
            reason=req.reason,
            triggering_policies=req.triggering_policies,
            triggering_source=req.triggering_source,
            expires_at=expires_at,
            created_at=now,
        )
        await self.db.execute(
            """INSERT INTO approvals
               (id, tenant_id, agent_id, action, context_hash, status,
                expires_at, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (approval_id, tenant_id, req.agent_id, req.action, context_hash,
             "pending", expires_at.isoformat(), record.model_dump_json(), now.isoformat()),
        )
        await self.db.commit()
        return record

    async def get_approval(self, approval_id: str, tenant_id: str) -> ApprovalRecord | None:
        cursor = await self.db.execute(
            "SELECT data FROM approvals WHERE id = ? AND tenant_id = ?",
            (approval_id, tenant_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ApprovalRecord.model_validate_json(row["data"])

    async def decide_approval(
        self, approval_id: str, decision: ApprovalDecision, decided_by: str, tenant_id: str
    ) -> ApprovalRecord | None:
        existing = await self.get_approval(approval_id, tenant_id)
        if existing is None:
            return None
        if existing.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval '{approval_id}' is already '{existing.status}'")

        now = _now()
        # Check expiry
        if existing.expires_at < now:
            existing.status = ApprovalStatus.EXPIRED
            await self.db.execute(
                "UPDATE approvals SET status = 'expired', data = ? WHERE id = ?",
                (existing.model_dump_json(), approval_id),
            )
            await self.db.commit()
            raise ValueError(f"Approval '{approval_id}' has expired")

        existing.status = decision.decision
        existing.decision_reason = decision.reason
        existing.decided_by = decided_by
        existing.decided_at = now

        await self.db.execute(
            "UPDATE approvals SET status = ?, decided_by = ?, decided_at = ?, data = ? WHERE id = ?",
            (decision.decision.value, decided_by, now.isoformat(),
             existing.model_dump_json(), approval_id),
        )
        await self.db.commit()
        return existing

    async def consume_approval(self, approval_id: str, tenant_id: str) -> bool:
        """Mark an approved request as consumed (one-time-use). Returns True if consumed."""
        approval = await self.get_approval(approval_id, tenant_id)
        if approval is None or approval.status != ApprovalStatus.APPROVED:
            return False
        now = _now()
        if approval.expires_at < now:
            return False

        approval.status = ApprovalStatus.CONSUMED
        approval.consumed_at = now
        await self.db.execute(
            "UPDATE approvals SET status = 'consumed', consumed_at = ?, data = ? WHERE id = ?",
            (now.isoformat(), approval.model_dump_json(), approval_id),
        )
        await self.db.commit()
        return True

    async def find_approved_for_context(
        self, agent_id: str, action: str, resource: str | None, tenant_id: str
    ) -> ApprovalRecord | None:
        """Find an approved (not consumed, not expired) request for a given context."""
        import hashlib, json as json_mod
        data = json_mod.dumps({"agent_id": agent_id, "action": action, "resource": resource or ""}, sort_keys=True)
        context_hash = hashlib.sha256(data.encode()).hexdigest()[:16]
        now = _now()
        cursor = await self.db.execute(
            """SELECT data FROM approvals
               WHERE tenant_id = ? AND context_hash = ? AND status = 'approved' AND expires_at > ?
               ORDER BY created_at DESC LIMIT 1""",
            (tenant_id, context_hash, now.isoformat()),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ApprovalRecord.model_validate_json(row["data"])

    async def list_pending_approvals(self, tenant_id: str, *, page: int = 1, page_size: int = 50) -> ApprovalList:
        now = _now()
        # Auto-expire old pending approvals
        await self.db.execute(
            "UPDATE approvals SET status = 'expired' WHERE tenant_id = ? AND status = 'pending' AND expires_at < ?",
            (tenant_id, now.isoformat()),
        )
        await self.db.commit()

        cursor = await self.db.execute(
            "SELECT COUNT(*) as cnt FROM approvals WHERE tenant_id = ? AND status = 'pending'", (tenant_id,)
        )
        row = await cursor.fetchone()
        total = row["cnt"]
        offset = (page - 1) * page_size
        cursor = await self.db.execute(
            """SELECT data FROM approvals WHERE tenant_id = ? AND status = 'pending'
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, offset),
        )
        rows = await cursor.fetchall()
        items = [ApprovalRecord.model_validate_json(r["data"]) for r in rows]
        return ApprovalList(items=items, total=total, page=page, page_size=page_size, has_more=(offset + page_size) < total)

    # --- Dashboard Queries ---

    async def get_fleet_summary(self, tenant_id: str) -> dict:
        """Compute fleet summary stats on the fly."""
        result = {}
        # Agents by status
        cursor = await self.db.execute(
            "SELECT status, COUNT(*) as cnt FROM agents WHERE tenant_id = ? GROUP BY status", (tenant_id,)
        )
        by_status = {}
        total = 0
        for row in await cursor.fetchall():
            by_status[row["status"]] = row["cnt"]
            total += row["cnt"]
        result["total_agents"] = total
        result["agents_by_status"] = by_status

        # Agents by platform
        cursor = await self.db.execute(
            "SELECT platform, COUNT(*) as cnt FROM agents WHERE tenant_id = ? GROUP BY platform", (tenant_id,)
        )
        result["agents_by_platform"] = {row["platform"]: row["cnt"] for row in await cursor.fetchall()}

        # Active in last 24h (agents with audit records in last 24h)
        from datetime import timedelta
        cutoff = (_now() - timedelta(hours=24)).isoformat()
        cursor = await self.db.execute(
            "SELECT COUNT(DISTINCT agent_id) as cnt FROM audit_records WHERE tenant_id = ? AND timestamp >= ?",
            (tenant_id, cutoff),
        )
        result["active_last_24h"] = (await cursor.fetchone())["cnt"]

        # Total audit records
        cursor = await self.db.execute(
            "SELECT COUNT(*) as cnt FROM audit_records WHERE tenant_id = ?", (tenant_id,)
        )
        result["total_audit_records"] = (await cursor.fetchone())["cnt"]

        # Policies
        cursor = await self.db.execute(
            "SELECT COUNT(*) as cnt FROM policies WHERE tenant_id = ?", (tenant_id,)
        )
        result["total_policies"] = (await cursor.fetchone())["cnt"]
        cursor = await self.db.execute(
            "SELECT COUNT(*) as cnt FROM policies WHERE tenant_id = ? AND enabled = 1", (tenant_id,)
        )
        result["total_policies_enabled"] = (await cursor.fetchone())["cnt"]

        return result

    async def get_top_consumers(self, tenant_id: str, *, limit: int = 10) -> list[dict]:
        """Get top agents by request count in current hourly period."""
        period_key = _now().strftime("%Y-%m-%dT%H")
        cursor = await self.db.execute(
            """SELECT bc.agent_id, bc.requests, bc.tokens_input + bc.tokens_output as tokens_total,
                      bc.cost_usd, a.name as agent_name, a.platform
               FROM budget_consumption bc
               LEFT JOIN agents a ON bc.agent_id = a.id AND bc.tenant_id = a.tenant_id
               WHERE bc.tenant_id = ? AND bc.period_type = 'hourly' AND bc.period_key = ?
               ORDER BY bc.requests DESC LIMIT ?""",
            (tenant_id, period_key, limit),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_recent_violations(self, tenant_id: str, *, limit: int = 50) -> list[dict]:
        """Get recent denied governance evaluations."""
        cursor = await self.db.execute(
            """SELECT timestamp, agent_id, action, result, data
               FROM audit_records
               WHERE tenant_id = ? AND action LIKE 'governance.evaluate:%' AND result = 'denied'
               ORDER BY sequence DESC LIMIT ?""",
            (tenant_id, limit),
        )
        rows = await cursor.fetchall()
        violations = []
        for row in rows:
            import json as json_mod
            try:
                data = json_mod.loads(row["data"])
            except Exception:
                data = {}
            violations.append({
                "timestamp": row["timestamp"],
                "agent_id": row["agent_id"],
                "action": row["action"].replace("governance.evaluate:", ""),
                "decision": "denied",
                "reason": data.get("detail"),
                "matched_policy_ids": data.get("metadata", {}).get("matched_policy_ids", []),
            })
        return violations

    async def get_approval_stats(self, tenant_id: str) -> dict:
        """Get approval flow statistics."""
        # Auto-expire first
        now = _now()
        await self.db.execute(
            "UPDATE approvals SET status = 'expired' WHERE tenant_id = ? AND status = 'pending' AND expires_at < ?",
            (tenant_id, now.isoformat()),
        )
        await self.db.commit()

        cursor = await self.db.execute(
            "SELECT status, COUNT(*) as cnt FROM approvals WHERE tenant_id = ? GROUP BY status", (tenant_id,)
        )
        stats = {"total_pending": 0, "total_approved": 0, "total_denied": 0, "total_expired": 0, "total_consumed": 0}
        for row in await cursor.fetchall():
            key = f"total_{row['status']}"
            if key in stats:
                stats[key] = row["cnt"]

        # Avg response time for decided approvals
        cursor = await self.db.execute(
            """SELECT AVG(
                 (julianday(decided_at) - julianday(created_at)) * 24 * 60
               ) as avg_minutes
               FROM approvals WHERE tenant_id = ? AND decided_at IS NOT NULL""",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        stats["avg_response_minutes"] = round(row["avg_minutes"], 1) if row["avg_minutes"] else None

        return stats
