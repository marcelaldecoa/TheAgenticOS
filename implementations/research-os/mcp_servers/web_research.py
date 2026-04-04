"""MCP server: web research via Tavily API with offline fallback."""

import json
import os
import re
from urllib.request import Request, urlopen
from urllib.error import URLError

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("web-research")

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")


@mcp.tool()
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web. Uses Tavily API if key is set, otherwise returns guidance."""
    if not TAVILY_API_KEY:
        return json.dumps(
            {
                "note": "TAVILY_API_KEY not set. Set it in your environment to enable live web search.",
                "query": query,
                "suggestion": "Try using fetch_page with specific URLs instead.",
            },
            indent=2,
        )

    try:
        payload = json.dumps(
            {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": min(max_results, 20),
                "include_answer": False,
            }
        ).encode()
        req = Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = [
            {"url": r["url"], "title": r["title"], "snippet": r.get("content", "")[:300]}
            for r in data.get("results", [])
        ]
        return json.dumps(results, indent=2)
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        return json.dumps({"error": str(e), "query": query})


@mcp.tool()
def fetch_page(url: str) -> str:
    """Fetch and extract main content from a web page."""
    try:
        req = Request(url, headers={"User-Agent": "AgenticOS-Research/1.0"})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError) as e:
        return json.dumps({"error": str(e), "url": url})

    # Strip HTML tags for a simple text extraction
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 10_000:
        text = text[:10_000] + "... (truncated)"

    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
    title = title_match.group(1).strip() if title_match else url

    return json.dumps({"url": url, "title": title, "content": text}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
