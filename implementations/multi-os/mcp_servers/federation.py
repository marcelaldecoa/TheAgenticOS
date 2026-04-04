"""MCP server: federation bus for cross-OS coordination.

Routes requests between domain OSs, enforces data classification,
tracks correlation IDs, and maintains an audit log.
"""

import json
import uuid
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("federation-bus")

# --- In-memory state --------------------------------------------------------

REGISTRY: dict[str, dict] = {
    "coding-os": {
        "capabilities": ["fix-bug", "new-feature", "code-review", "investigate-code", "assess-effort"],
        "max_classification": "confidential",
    },
    "research-os": {
        "capabilities": ["competitive-analysis", "literature-review", "web-search", "source-evaluation"],
        "max_classification": "internal",
    },
    "support-os": {
        "capabilities": ["triage-ticket", "resolve-issue", "investigate-issue", "draft-response", "escalation"],
        "max_classification": "confidential",
    },
    "knowledge-os": {
        "capabilities": ["store-knowledge", "search-knowledge", "validate-freshness", "answer-question"],
        "max_classification": "internal",
    },
}

CLASSIFICATION_LEVELS = {"public": 0, "internal": 1, "confidential": 2}

AUDIT_LOG: list[dict] = []
MESSAGE_LOG: list[dict] = []


def _log_audit(action: str, details: dict) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        **details,
    }
    AUDIT_LOG.append(entry)


# --- Tools ------------------------------------------------------------------


@mcp.tool()
def discover_capabilities() -> str:
    """List all registered OSs and their capabilities."""
    return json.dumps(
        {name: info["capabilities"] for name, info in REGISTRY.items()},
        indent=2,
    )


@mcp.tool()
def find_os_for(capability: str) -> str:
    """Find which OS provides a given capability."""
    for name, info in REGISTRY.items():
        if capability in info["capabilities"]:
            return json.dumps({"os": name, "capability": capability})
    return json.dumps({"error": f"No OS provides capability '{capability}'"})


@mcp.tool()
def send_request(
    target_os: str,
    capability: str,
    description: str,
    data_classification: str = "internal",
    correlation_id: str = "",
) -> str:
    """Send a request to a target OS. Enforces data classification at boundaries."""
    if target_os not in REGISTRY:
        return json.dumps({"error": f"Unknown OS: {target_os}"})

    target_max = CLASSIFICATION_LEVELS.get(REGISTRY[target_os]["max_classification"], 1)
    data_level = CLASSIFICATION_LEVELS.get(data_classification, 1)

    if data_level > target_max:
        _log_audit("BLOCKED", {
            "target": target_os,
            "capability": capability,
            "reason": f"Data classification '{data_classification}' exceeds {target_os} clearance '{REGISTRY[target_os]['max_classification']}'",
        })
        return json.dumps({
            "error": f"Cannot send '{data_classification}' data to {target_os} (clearance: '{REGISTRY[target_os]['max_classification']}'). Redact to '{REGISTRY[target_os]['max_classification']}' or lower.",
        })

    if not correlation_id:
        correlation_id = f"fed-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"

    msg = {
        "id": uuid.uuid4().hex[:8],
        "correlation_id": correlation_id,
        "target_os": target_os,
        "capability": capability,
        "description": description,
        "data_classification": data_classification,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "delivered",
    }
    MESSAGE_LOG.append(msg)
    _log_audit("SENT", {"target": target_os, "capability": capability, "correlation_id": correlation_id})

    return json.dumps({
        "status": "delivered",
        "correlation_id": correlation_id,
        "message_id": msg["id"],
        "target_os": target_os,
        "capability": capability,
        "note": f"Request delivered to {target_os}. The delegate agent for this OS will handle it.",
    }, indent=2)


@mcp.tool()
def get_audit_trail(correlation_id: str = "") -> str:
    """Get the audit trail, optionally filtered by correlation ID."""
    if correlation_id:
        entries = [e for e in AUDIT_LOG if e.get("correlation_id") == correlation_id]
    else:
        entries = AUDIT_LOG[-20:]
    return json.dumps(entries, indent=2) if entries else json.dumps({"message": "No audit entries found"})


@mcp.tool()
def register_os(name: str, capabilities: str, max_classification: str = "internal") -> str:
    """Register or update an OS in the federation. Capabilities are comma-separated."""
    REGISTRY[name] = {
        "capabilities": [c.strip() for c in capabilities.split(",")],
        "max_classification": max_classification,
    }
    _log_audit("REGISTERED", {"os": name, "capabilities": REGISTRY[name]["capabilities"]})
    return f"Registered OS '{name}' with capabilities: {REGISTRY[name]['capabilities']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
