# Appendix A: Mapping to Today's Stack

This appendix bridges the Agentic OS architecture to the tools, frameworks, and SDKs available today. The field moves fast — specific versions and APIs will change — but the mapping from abstract architecture to concrete technology categories is durable.

The goal is not to recommend a specific stack but to show how each architectural layer maps to real implementation choices, so you can evaluate your own tools against the model.

## Cognitive Kernel

The kernel — intent routing, planning, decomposition, scheduling — maps to **orchestration frameworks**.

### Frameworks

| Framework | Kernel Capabilities | Best For |
|---|---|---|
| **LangGraph** (LangChain) | Stateful graph-based orchestration, conditional routing, tool calling, human-in-the-loop | Complex multi-step workflows with branching logic and state persistence |
| **Semantic Kernel** (Microsoft) | Planner with automatic function composition, plugin model, multi-model orchestration | .NET/Python systems needing planning over a plugin ecosystem |
| **AutoGen** (Microsoft) | Multi-agent conversation patterns, group chat orchestration, code execution | Research and prototyping of multi-agent systems |
| **CrewAI** | Role-based agent teams, task delegation, sequential and parallel workflows | Team-of-agents scenarios with defined roles (researcher, writer, reviewer) |
| **OpenAI Assistants API** | Built-in threads, tool use, code interpreter, file handling | Single-agent applications leveraging OpenAI's managed infrastructure |
| **Amazon Bedrock Agents** | Managed agent orchestration, action groups, knowledge bases | AWS-native deployments needing managed agent infrastructure |
| **Google ADK** (Agent Development Kit) | Multi-agent systems, tool use, orchestration | Google Cloud-native agent systems |

### Implementation Guidance

**Start with a single orchestration framework.** The kernel abstraction does not require building a custom orchestrator from scratch. The reference implementations in Part VI use the **Microsoft Agent Framework (Semantic Kernel)** — it provides `ChatCompletionAgent` for individual workers, orchestration patterns (Sequential, Concurrent, Handoff, GroupChat) for coordination, and plugins (`@kernel_function`) for tool integration.

**The kernel loop** (perceive → interpret → plan → delegate → monitor → consolidate → adapt) maps to orchestration patterns. In Semantic Kernel, the orchestration type determines the coordination model:

```text
Agentic OS Concept    →  Semantic Kernel Implementation
───────────────────────────────────────────────────────
Intent Router         →  Agent with routing logic or HandoffOrchestration
Planner               →  Agent with planning instructions
Workers               →  ChatCompletionAgent instances with scoped plugins
Pipeline              →  SequentialOrchestration
Fan-Out/Fan-In        →  ConcurrentOrchestration
Adversarial Review    →  GroupChatOrchestration
Dynamic Routing       →  HandoffOrchestration
Tools/Operators       →  Plugins (@kernel_function) and MCP servers
Governance            →  Function filters (on_function_invocation)
```

## Process Fabric

The process fabric — worker lifecycle, sandboxing, isolation — maps to **agent runtimes and execution environments**.

### Approaches

| Approach | Isolation Level | Use When |
|---|---|---|
| **In-process agents** (LangGraph nodes, Semantic Kernel functions) | None — shared memory space | Trusted workers, low security requirements, maximum speed |
| **Containerized workers** (Docker, Kubernetes Jobs) | Process-level isolation | Workers need distinct dependencies, security boundaries, or resource limits |
| **Serverless functions** (AWS Lambda, Azure Functions) | Function-level isolation | Short-lived, stateless workers with burst scaling needs |
| **Code sandboxes** (E2B, Modal, Docker-in-Docker) | Full sandboxing | Workers execute untrusted code; security is critical |
| **MCP Servers** (Model Context Protocol) | Service-level isolation | Workers connect to external tools through a standardized protocol |

### Worker Contracts in Practice

The scoped worker contract maps to how you configure an agent's system prompt, tools, and constraints:

```python
# Semantic Kernel example
worker = kernel.create_agent(
    name="code_reviewer",
    instructions="Review the code diff for quality, security, and style issues.",
    tools=[file_read, git_diff, comment_create],  # scoped capabilities
    max_tokens=4000,                                # resource envelope
    temperature=0.1                                 # determinism preference
)
```

```python
# LangGraph example
def code_review_node(state):
    """Scoped worker contract: reviews code with specific tools."""
    return model.invoke(
        messages=[SystemMessage(content=REVIEW_INSTRUCTIONS)],
        tools=[file_read, git_diff],  # capability scoping
    )
```

## Memory Plane

The memory plane — working, episodic, semantic, procedural memory — maps to **storage and retrieval systems**.

### Technology Mapping

| Memory Tier | Technology Options | Key Considerations |
|---|---|---|
| **Working Memory** | In-context (prompt), state objects (LangGraph state, thread messages) | Limited by context window; assemble carefully |
| **Episodic Memory** | PostgreSQL, MongoDB, Redis (structured event storage) | Schema should capture: event, timestamp, outcome, metadata |
| **Semantic Memory** | Vector databases (Pinecone, Weaviate, Qdrant, Chroma, pgvector) | Embedding model choice affects retrieval quality; chunk size matters |
| **Procedural Memory** | Document stores, skill registries, instruction databases | Version controlled; retrievable by task type |
| **Cross-session State** | Redis, DynamoDB, PostgreSQL with JSONB | Must survive process restarts; keyed by session/user/project |

### Retrieval-Augmented Generation (RAG)

The Memory on Demand pattern maps directly to RAG. Implementation choices:

- **Embedding model**: Use a model matched to your domain. OpenAI `text-embedding-3-large`, Cohere `embed-v4`, or open-source alternatives (BGE, E5).
- **Chunking strategy**: Chunk by semantic unit (paragraph, function, section), not by fixed token count. Overlap chunks by 10-20% for context continuity.
- **Retrieval**: Hybrid search (vector similarity + keyword BM25) outperforms either alone. Tools like LangChain retrievers, LlamaIndex, or direct vector DB queries implement this.
- **Reranking**: After initial retrieval, rerank results with a cross-encoder (Cohere Rerank, Jina Reranker) to improve precision before inserting into the context window.

### Memory in Multi-Agent Systems

When multiple agents need shared memory, use an **Operational State Board** backed by a shared data store:

```python
# Shared state via LangGraph
class TaskState(TypedDict):
    plan: list[str]
    completed: list[str]
    findings: dict[str, str]
    blockers: list[str]

# All workers read from and write to this shared state
graph = StateGraph(TaskState)
```

## Governance Plane

The governance plane — policies, permissions, audit, approval gates — maps to **guardrails, observability, and authorization systems**.

### Technology Mapping

| Governance Function | Technology Options |
|---|---|
| **Policy enforcement (input/output)** | Guardrails AI, NeMo Guardrails, custom middleware |
| **Content filtering** | Azure AI Content Safety, OpenAI Moderation API, Lakera Guard |
| **Permission management** | OPA (Open Policy Agent), Cedar (AWS), custom RBAC |
| **Approval workflows** | Slack/Teams integrations, custom approval UIs, human-in-the-loop nodes in LangGraph |
| **Audit logging** | Structured logging (OpenTelemetry), LangSmith, Arize Phoenix, Langfuse |
| **Cost tracking** | LLM provider dashboards, custom token counters, LangSmith cost tracking |
| **Observability** | LangSmith, Langfuse, Arize Phoenix, Weights & Biases Weave, OpenLLMetry |

### Implementation: Governance as Middleware

The governance middleware pattern maps to interceptors or callbacks that wrap tool and model calls:

```python
# Guardrails as middleware (pseudo-code)
class GovernanceMiddleware:
    def before_tool_call(self, tool, args, worker_context):
        # Capability check
        if tool.name not in worker_context.allowed_tools:
            raise PermissionDenied(f"Worker lacks capability: {tool.name}")
        # Risk check
        if tool.risk_level == "high" and not worker_context.has_approval:
            return request_human_approval(tool, args)
        # Budget check
        if worker_context.budget_remaining <= 0:
            raise BudgetExhausted()
        # Audit
        log_action(tool, args, worker_context)

    def after_tool_call(self, tool, args, result, worker_context):
        # Output validation
        validate_output(result, tool.output_schema)
        # Audit
        log_result(tool, result, worker_context)
```

### Human-in-the-Loop

Approval gates map to interrupt nodes in orchestration frameworks:

- **LangGraph**: `interrupt_before` / `interrupt_after` on graph nodes. The graph pauses, persists state, and resumes after human approval.
- **Semantic Kernel**: Filters and function invocation handlers that can pause execution.
- **Custom**: Webhook-based approval flows that pause a task and resume on callback.

## Tool & Skill Layer

Tools map to **function calling, MCP servers, and API integrations**.

### Model Context Protocol (MCP)

MCP is emerging as the standard protocol for connecting agents to tools. Key properties:

- **Standardized interface**: Tools expose capabilities through a uniform protocol (JSON-RPC over stdio or HTTP).
- **Discovery**: Agents discover available tools through the MCP server's capability listing.
- **Isolation**: Each MCP server runs as an independent process with its own permissions.
- **Ecosystem**: Growing registry of MCP servers for common integrations (GitHub, databases, file systems, web search).

MCP maps directly to the Operator Fabric's tool registry pattern: tools declare their inputs, outputs, and capabilities; the kernel discovers and selects them at runtime.

### Function Calling

All major model providers support function calling (tool use):

- **OpenAI**: `tools` parameter with JSON schema definitions.
- **Anthropic**: `tools` parameter with input schema.
- **Google (Gemini)**: Function declarations with parameter schemas.
- **Azure OpenAI**: Same as OpenAI, with enterprise security layers.

Function calling is the atomic mechanism. MCP and orchestration frameworks build higher-level abstractions on top of it.

## Model Provider Layer

The model provider abstraction maps to **LLM APIs and routing layers**.

### Multi-Model Strategy

| Task Type | Model Tier | Examples |
|---|---|---|
| Classification, routing | Small/fast | GPT-4.1 mini, Claude Haiku, Gemini Flash |
| Code generation, analysis | Medium | GPT-4.1, Claude Sonnet, Gemini Pro |
| Complex reasoning, planning | Large | Claude Opus, o3, Gemini Ultra |
| Embeddings | Embedding-specific | text-embedding-3-large, Cohere embed-v4 |

### Model Routers

Tools for implementing the model provider abstraction:

- **LiteLLM**: Unified API across 100+ LLM providers with fallback, load balancing, and cost tracking.
- **OpenRouter**: Multi-provider routing with automatic failover.
- **Custom routing**: Select model based on task type, cost budget, and required capabilities.

```python
# Model selection based on task (pseudo-code)
def select_model(task_type, budget):
    if task_type == "classification":
        return "gpt-4.1-mini"  # fast, cheap
    elif task_type == "planning" and budget.allows("premium"):
        return "claude-opus-4"  # best reasoning
    elif task_type == "code_generation":
        return "claude-sonnet-4"  # strong code, moderate cost
    else:
        return "gpt-4.1"  # good default
```

## Putting It Together: A Starter Architecture

For a team building their first Agentic OS, here is a practical starting stack:

| Layer | Starting Choice | Why |
|---|---|---|
| **Kernel** | Semantic Kernel (Python) | Agent Framework with built-in orchestration patterns (Sequential, Handoff, GroupChat), plugin model, and multi-model support |
| **Process Fabric** | `ChatCompletionAgent` + E2B for code execution | Each agent is a scoped worker with its own plugins; E2B for sandboxed code execution |
| **Memory** | pgvector (semantic) + PostgreSQL (episodic) | Single database for both vector and structured storage |
| **Governance** | SK function filters + Langfuse (observability) | Filters enforce policies at every function call; Langfuse for tracing and cost tracking |
| **Tools** | SK Plugins (`@kernel_function`) + MCP servers | Plugins for local tools; MCP servers for isolated/external tools |
| **Models** | Azure OpenAI (via SK connectors) | Native SK integration; multi-model via service selection |

This stack can be deployed as a single application initially and decomposed into services as scale demands.

## What This Mapping Is Not

This appendix maps architecture to tools, not tools to architecture. Do not pick a tool and design the architecture around it. Design the architecture from the principles in this book, then select tools that implement each layer.

Tools change yearly. The architecture endures. If you find yourself locked into a specific framework's patterns, you have coupled too tightly. The reference architecture's layer boundaries exist precisely so that you can replace any tool without rebuilding the system.
