"""MCP server: scoped filesystem access."""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem")

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", ".")).resolve()


def _safe_path(rel: str) -> Path:
    target = (PROJECT_ROOT / rel).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"Path traversal blocked: {rel}")
    return target


@mcp.tool()
def file_read(path: str) -> str:
    """Read a file from the project directory."""
    try:
        target = _safe_path(path)
    except ValueError as e:
        return f"Error: {e}"
    if not target.is_file():
        return f"Error: {path} not found"
    content = target.read_text(encoding="utf-8")
    if len(content) > 50_000:
        content = content[:50_000] + "\n... (truncated)"
    return content


@mcp.tool()
def file_write(path: str, content: str) -> str:
    """Write content to a file in the project directory."""
    try:
        target = _safe_path(path)
    except ValueError as e:
        return f"Error: {e}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


@mcp.tool()
def file_search(pattern: str) -> str:
    """Search for files matching a glob pattern in the project directory."""
    try:
        matches = sorted(PROJECT_ROOT.glob(pattern))
    except ValueError:
        return "Error: invalid glob pattern"
    results = [str(m.relative_to(PROJECT_ROOT)) for m in matches if m.is_file()]
    if len(results) > 50:
        results = results[:50]
    return "\n".join(results) if results else "No files matched"


if __name__ == "__main__":
    mcp.run(transport="stdio")
