"""MCP server: knowledge store with in-memory storage.

Provides artifact storage, keyword-based search, linking, and staleness
detection. In production this would use PostgreSQL + pgvector.
"""

import json
import uuid
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("knowledge-store")

# --- In-memory store --------------------------------------------------------

ARTIFACTS: dict[str, dict] = {}
LINKS: list[dict] = []


def _match_score(query: str, artifact: dict) -> float:
    text = f"{artifact['title']} {artifact['content']} {' '.join(artifact['tags'])}".lower()
    words = query.lower().split()
    return sum(1 for w in words if w in text) / max(len(words), 1)


# --- Tools ------------------------------------------------------------------


@mcp.tool()
def store_artifact(
    title: str,
    content: str,
    source: str,
    tags: str,
    classification: str = "internal",
) -> str:
    """Store a knowledge artifact. Tags are comma-separated. Classification: public, internal, or confidential."""
    if classification not in ("public", "internal", "confidential"):
        return f"Error: classification must be public, internal, or confidential (got '{classification}')"
    aid = str(uuid.uuid4())[:8]
    ARTIFACTS[aid] = {
        "id": aid,
        "title": title,
        "content": content,
        "source": source,
        "tags": [t.strip() for t in tags.split(",")],
        "classification": classification,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return f"Stored artifact {aid}: {title}"


@mcp.tool()
def search(query: str, max_classification: str = "internal", limit: int = 10) -> str:
    """Search knowledge artifacts. Respects classification access control."""
    clearance = {"public": 0, "internal": 1, "confidential": 2}
    max_level = clearance.get(max_classification, 1)

    scored = []
    for a in ARTIFACTS.values():
        a_level = clearance.get(a["classification"], 1)
        if a_level > max_level:
            continue
        score = _match_score(query, a)
        if score > 0:
            scored.append({
                "id": a["id"],
                "title": a["title"],
                "content": a["content"][:300],
                "source": a["source"],
                "classification": a["classification"],
                "similarity": round(score, 2),
            })
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return json.dumps(scored[:limit], indent=2) if scored else json.dumps([])


@mcp.tool()
def link_artifacts(from_id: str, to_id: str, relation: str) -> str:
    """Link two knowledge artifacts with a relationship type."""
    if from_id not in ARTIFACTS:
        return f"Error: artifact {from_id} not found"
    if to_id not in ARTIFACTS:
        return f"Error: artifact {to_id} not found"
    LINKS.append({
        "from_id": from_id,
        "to_id": to_id,
        "relation": relation,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    return f"Linked {from_id} --[{relation}]--> {to_id}"


@mcp.tool()
def find_stale(max_age_days: int = 90) -> str:
    """Find artifacts not updated in the specified number of days."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    stale = []
    for a in ARTIFACTS.values():
        updated = datetime.fromisoformat(a["updated_at"])
        if updated < cutoff:
            age = (datetime.now() - updated).days
            stale.append({
                "id": a["id"],
                "title": a["title"],
                "source": a["source"],
                "updated_at": a["updated_at"],
                "age_days": age,
            })
    stale.sort(key=lambda x: x["age_days"], reverse=True)
    return json.dumps(stale[:50], indent=2) if stale else json.dumps({"message": "No stale artifacts found"})


@mcp.tool()
def get_artifact(artifact_id: str) -> str:
    """Get a specific artifact by ID, including its links."""
    a = ARTIFACTS.get(artifact_id)
    if not a:
        return json.dumps({"error": f"Artifact {artifact_id} not found"})
    related = [lk for lk in LINKS if lk["from_id"] == artifact_id or lk["to_id"] == artifact_id]
    return json.dumps({**a, "links": related}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
