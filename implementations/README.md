# Agentic OS — Reference Implementations

Each folder is a self-contained workspace implementing one of the case studies from Part VI of the book. Open any folder as a VS Code workspace to use its agents, skills, and MCP integrations with GitHub Copilot.

## Implementations

### `coding-os/`

A Coding OS for software development — agents for coding, testing, and reviewing.

| Component | Files |
|-----------|-------|
| **Agents** | `@coder` (implementation), `@tester` (tests), `@reviewer` (quality review) |
| **Skills** | `/fix-bug` (reproduce → diagnose → fix → verify), `/new-feature` (plan → implement → test → review), `/code-review` (structured quality assessment) |
| **Instructions** | Python standards (PEP 8, type hints), Testing standards (pytest) |
| **MCP** | `filesystem` (scoped file access), `git` (version control) |

### `research-os/`

A Research OS for conducting rigorous research — agents for scouting, analysis, and critique.

| Component | Files |
|-----------|-------|
| **Agents** | `@scout` (broad search), `@analyst` (deep source evaluation), `@critic` (adversarial review) |
| **Skills** | `/competitive-analysis` (market comparison workflow), `/literature-review` (academic survey workflow) |
| **Instructions** | Research output standards (citation requirements, confidence calibration) |
| **MCP** | `web-research` (Tavily search + page extraction) |

### `support-os/`

A Support OS for customer support — agents for triage, resolution, and escalation.

| Component | Files |
|-----------|-------|
| **Agents** | `@triage` (classify and route), `@resolver` (apply known fixes), `@investigator` (diagnose unknowns) |
| **Skills** | `/triage-and-resolve` (end-to-end ticket handling), `/escalation` (human handoff packaging) |
| **Instructions** | (via copilot-instructions.md — data governance, PII rules) |
| **MCP** | `support-tools` (customer context, logs, cache ops), `knowledge-base` (known issue search) |

### `knowledge-os/`

A Knowledge OS for organizational knowledge management — agents for harvesting and validation.

| Component | Files |
|-----------|-------|
| **Agents** | `@harvester` (extract knowledge from raw content), `@validator` (check freshness) |
| **Skills** | `/harvest-knowledge` (capture workflow), `/validate-freshness` (maintenance sweep) |
| **Instructions** | (via copilot-instructions.md — classification, provenance) |
| **MCP** | `knowledge-store` (PostgreSQL + pgvector knowledge graph) |

### `multi-os/`

Multi-OS federation — a coordinator that routes work across independent OSs.

| Component | Files |
|-----------|-------|
| **Agents** | `@coordinator` (cross-OS orchestration), `@coding-delegate`, `@support-delegate`, `@knowledge-delegate` (OS-specific delegates) |
| **Instructions** | Federation governance (data classification, PII redaction, correlation IDs) |
| **MCP** | `federation-bus` (cross-OS message routing) |

## How to Use

1. **Open** any implementation folder as a VS Code workspace
2. **Chat** with Copilot — the `copilot-instructions.md` is automatically loaded
3. **Invoke agents** directly: `@coder`, `@tester`, `@scout`, etc.
4. **Use skills** via `/`: `/fix-bug`, `/competitive-analysis`, `/harvest-knowledge`, etc.
5. **MCP servers** connect automatically if the required environment variables are set

## Architecture Mapping

| Agentic OS Layer | VS Code Copilot Primitive |
|---|---|
| Cognitive Kernel | `copilot-instructions.md` + orchestration logic in agents |
| Workers / Subagents | `.agent.md` files with scoped tools |
| Skills / Strategies | `SKILL.md` files with step-by-step procedures |
| Tool Layer / Operators | MCP servers (`.vscode/mcp.json`) |
| Governance | Instructions + agent constraints + tool scoping |
| Memory | MCP-backed storage (pgvector, PostgreSQL) |
