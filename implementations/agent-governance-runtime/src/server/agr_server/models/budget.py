"""Budget and quota tracking models.

Tracks resource consumption per agent per time period.
Request-count limits are hard-enforced; cost/token limits are warning-only in Phase 2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BudgetConsumeRequest(BaseModel):
    """Record a consumption event for an agent."""

    agent_id: str
    requests: int = Field(default=1, ge=0, description="Number of requests consumed")
    tokens_input: int = Field(default=0, ge=0)
    tokens_output: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    action: str | None = Field(default=None, description="Action that caused consumption")
    metadata: dict[str, Any] = Field(default_factory=dict)


class BudgetPeriodUsage(BaseModel):
    """Consumption within a time period (hourly or daily)."""

    period: str = Field(description="Period key, e.g. '2026-04-16T19' (hourly) or '2026-04-16' (daily)")
    requests: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0


class BudgetStatus(BaseModel):
    """Current budget status for an agent."""

    agent_id: str
    hourly_usage: BudgetPeriodUsage | None = None
    daily_usage: BudgetPeriodUsage | None = None

    # Limits (from agent's access profile)
    max_requests_per_hour: int | None = None
    max_tokens_per_hour: int | None = None
    max_cost_per_day_usd: float | None = None

    # Computed status
    status: str = Field(
        default="ok",
        description="ok | warning | exceeded",
    )
    warnings: list[str] = Field(default_factory=list)

    def compute_status(self) -> None:
        """Recompute status based on usage vs limits."""
        self.warnings = []
        self.status = "ok"

        if self.max_requests_per_hour and self.hourly_usage:
            ratio = self.hourly_usage.requests / self.max_requests_per_hour
            if ratio >= 1.0:
                self.status = "exceeded"
                self.warnings.append(
                    f"Request limit exceeded: {self.hourly_usage.requests}/{self.max_requests_per_hour} per hour"
                )
            elif ratio >= 0.8:
                if self.status != "exceeded":
                    self.status = "warning"
                self.warnings.append(
                    f"Request limit at {ratio:.0%}: {self.hourly_usage.requests}/{self.max_requests_per_hour} per hour"
                )

        if self.max_tokens_per_hour and self.hourly_usage:
            total_tokens = self.hourly_usage.tokens_input + self.hourly_usage.tokens_output
            ratio = total_tokens / self.max_tokens_per_hour
            if ratio >= 1.0:
                if self.status != "exceeded":
                    self.status = "warning"  # Token limits are soft
                self.warnings.append(
                    f"Token limit exceeded (soft): {total_tokens}/{self.max_tokens_per_hour} per hour"
                )
            elif ratio >= 0.8:
                if self.status == "ok":
                    self.status = "warning"
                self.warnings.append(
                    f"Token usage at {ratio:.0%}: {total_tokens}/{self.max_tokens_per_hour} per hour"
                )

        if self.max_cost_per_day_usd and self.daily_usage:
            ratio = self.daily_usage.cost_usd / self.max_cost_per_day_usd
            if ratio >= 1.0:
                if self.status != "exceeded":
                    self.status = "warning"  # Cost limits are soft
                self.warnings.append(
                    f"Daily cost limit exceeded (soft): ${self.daily_usage.cost_usd:.4f}/${self.max_cost_per_day_usd:.2f}"
                )
            elif ratio >= 0.8:
                if self.status == "ok":
                    self.status = "warning"
                self.warnings.append(
                    f"Daily cost at {ratio:.0%}: ${self.daily_usage.cost_usd:.4f}/${self.max_cost_per_day_usd:.2f}"
                )
