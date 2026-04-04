"""MCP server: git operations."""

import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("git")


def _run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output[:10_000] if output else "(no output)"
    except FileNotFoundError:
        return "Error: git not found on PATH"
    except subprocess.TimeoutExpired:
        return "Error: git command timed out"


@mcp.tool()
def git_diff(ref: str = "HEAD") -> str:
    """Get the diff of current changes against a git reference."""
    return _run_git("diff", ref)


@mcp.tool()
def git_log(count: int = 10) -> str:
    """Get recent commit history."""
    return _run_git("log", f"-{count}", "--oneline")


@mcp.tool()
def git_create_branch(name: str) -> str:
    """Create and checkout a new git branch."""
    return _run_git("checkout", "-b", name)


if __name__ == "__main__":
    mcp.run(transport="stdio")
