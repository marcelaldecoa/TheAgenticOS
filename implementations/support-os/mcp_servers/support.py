"""MCP server: support tools with in-memory sample data.

Provides customer context (no PII), known-issue search, cache operations,
and log search for the Support OS tutorial.
"""

import json
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("support-tools")

# --- Sample data (in-memory) -----------------------------------------------

KNOWN_ISSUES = [
    {
        "id": "KI-847",
        "title": "Dashboard timeout for large datasets (>10K rows)",
        "symptoms": "dashboard loading spinner stuck timeout large dataset slow",
        "resolution": "Invalidate the dashboard cache for the affected account.",
        "severity": "medium",
    },
    {
        "id": "KI-623",
        "title": "Password reset email delayed up to 30 minutes",
        "symptoms": "password reset email not received delayed login",
        "resolution": "Check spam folder. If not found, trigger manual reset via admin panel.",
        "severity": "low",
    },
    {
        "id": "KI-901",
        "title": "CSV export fails for files over 5MB",
        "symptoms": "csv export error 500 timeout large file download",
        "resolution": "Known issue in export service v2.4. Workaround: export in smaller batches.",
        "severity": "high",
    },
    {
        "id": "KI-512",
        "title": "API rate limit returns 429 without retry-after header",
        "symptoms": "api rate limit 429 throttle retry header missing",
        "resolution": "Use exponential backoff. Fix scheduled for next release.",
        "severity": "medium",
    },
]

CUSTOMERS = {
    "T-4521": {"plan": "pro", "tenure_months": 14, "past_tickets_count": 3, "sentiment_trend": "neutral"},
    "T-8812": {"plan": "enterprise", "tenure_months": 24, "past_tickets_count": 1, "sentiment_trend": "positive"},
    "T-3309": {"plan": "free", "tenure_months": 2, "past_tickets_count": 8, "sentiment_trend": "frustrated"},
    "default": {"plan": "pro", "tenure_months": 6, "past_tickets_count": 0, "sentiment_trend": "neutral"},
}

LOG_ENTRIES = []
_now = datetime.now()
for i, msg in enumerate(
    [
        "INFO  | Export service started",
        "INFO  | User login successful",
        "WARN  | Slow query detected: dashboard_data (3200ms)",
        "ERROR | TimeoutError in export service at /api/export/csv",
        "INFO  | Cache invalidated for account A-1234",
        "ERROR | OOM kill: export service pid=4821 (memory: 2.1GB)",
        "WARN  | Deployment: export-service v2.4 rolled out",
        "INFO  | Health check passed",
        "ERROR | Connection refused: search-service:9200",
        "INFO  | Cache rebuild completed",
    ]
):
    LOG_ENTRIES.append(
        {
            "timestamp": (_now - timedelta(hours=10 - i)).isoformat(timespec="seconds"),
            "level": msg.split("|")[0].strip(),
            "message": msg.split("|")[1].strip(),
        }
    )

CACHE_STATE: dict[str, list[str]] = {}


# --- Tools ------------------------------------------------------------------


@mcp.tool()
def search_known_issues(symptoms: str) -> str:
    """Search for known issues matching the described symptoms."""
    symptoms_lower = symptoms.lower()
    scored = []
    for ki in KNOWN_ISSUES:
        keywords = ki["symptoms"].split()
        score = sum(1 for kw in keywords if kw in symptoms_lower)
        if score > 0:
            scored.append(
                {
                    "id": ki["id"],
                    "title": ki["title"],
                    "resolution": ki["resolution"],
                    "confidence": round(min(score / 4, 1.0), 2),
                }
            )
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    return json.dumps(scored[:5], indent=2) if scored else json.dumps([])


@mcp.tool()
def get_customer_context(ticket_id: str) -> str:
    """Get customer context for a ticket. Returns plan, tenure, and ticket history — NO PII."""
    customer = CUSTOMERS.get(ticket_id, CUSTOMERS["default"])
    ctx = {
        "ticket_id": ticket_id,
        "plan": customer["plan"],
        "tenure_months": customer["tenure_months"],
        "past_tickets_count": customer["past_tickets_count"],
        "sentiment_trend": customer["sentiment_trend"],
        "note": "Governance: PII fields are NOT included.",
    }
    return json.dumps(ctx, indent=2)


@mcp.tool()
def invalidate_cache(account_id: str, cache_type: str = "dashboard") -> str:
    """Invalidate cache for a customer account. Safe, reversible operation."""
    CACHE_STATE.setdefault(account_id, []).append(cache_type)
    return f"Cache '{cache_type}' invalidated for account {account_id}."


@mcp.tool()
def search_logs(query: str, account_id: str = "", hours: int = 24) -> str:
    """Search application logs. Returns matching entries (max 50)."""
    query_lower = query.lower()
    cutoff = datetime.now() - timedelta(hours=hours)
    results = []
    for entry in LOG_ENTRIES:
        ts = datetime.fromisoformat(entry["timestamp"])
        if ts < cutoff:
            continue
        if query_lower in entry["message"].lower() or (account_id and account_id.lower() in entry["message"].lower()):
            results.append(entry)
    return json.dumps(results[:50], indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
