"""MCP server: knowledge base for support known-issues search.

Provides vector-style similarity search over known issues using keyword matching.
In production, this would use pgvector or a dedicated vector store.
"""

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("knowledge-base")

# Same issues as support.py so the two MCP servers share a consistent data set
ARTICLES = [
    {
        "id": "KB-001",
        "title": "Dashboard timeout for large datasets",
        "content": "When a user has more than 10,000 rows in their dataset, the dashboard may time out during initial load. This is caused by an unoptimized aggregation query. Workaround: invalidate the dashboard cache for the account. Fix ETA: Q3 release.",
        "tags": ["dashboard", "performance", "timeout"],
    },
    {
        "id": "KB-002",
        "title": "Password reset email delays",
        "content": "Password reset emails may be delayed up to 30 minutes during peak hours due to email queue prioritization. Users should check spam folders. If the email does not arrive after 30 minutes, use the admin manual reset endpoint.",
        "tags": ["authentication", "email", "password"],
    },
    {
        "id": "KB-003",
        "title": "CSV export service memory issues (v2.4)",
        "content": "Export service v2.4 introduced a memory-intensive encoding step for non-ASCII character support. Exports larger than 5MB trigger an OOM kill. Workaround: export in batches of 5000 rows or fewer. Rollback to v2.3 is approved if needed.",
        "tags": ["export", "csv", "memory", "encoding"],
    },
    {
        "id": "KB-004",
        "title": "API rate limiting missing retry-after header",
        "content": "The API returns 429 responses without a Retry-After header when rate limits are exceeded. Clients should implement exponential backoff with a starting interval of 1 second. Header will be added in the next API version.",
        "tags": ["api", "rate-limit", "429"],
    },
    {
        "id": "KB-005",
        "title": "Search service connection errors after restart",
        "content": "After the search service (Elasticsearch) restarts, connections from the application may fail for 30-60 seconds while the cluster stabilizes. The health check endpoint will return 503 during this window.",
        "tags": ["search", "elasticsearch", "connection"],
    },
]


@mcp.tool()
def search_articles(query: str, limit: int = 5) -> str:
    """Search the knowledge base for articles matching a query."""
    query_lower = query.lower()
    scored = []
    for article in ARTICLES:
        text = f"{article['title']} {article['content']} {' '.join(article['tags'])}".lower()
        words = query_lower.split()
        score = sum(1 for w in words if w in text)
        if score > 0:
            scored.append({**article, "relevance": round(score / max(len(words), 1), 2)})
    scored.sort(key=lambda x: x["relevance"], reverse=True)
    return json.dumps(scored[:limit], indent=2) if scored else json.dumps([])


@mcp.tool()
def get_article(article_id: str) -> str:
    """Get a specific knowledge base article by ID."""
    for article in ARTICLES:
        if article["id"] == article_id:
            return json.dumps(article, indent=2)
    return json.dumps({"error": f"Article {article_id} not found"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
