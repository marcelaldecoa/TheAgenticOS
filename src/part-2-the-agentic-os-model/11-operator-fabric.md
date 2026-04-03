# Operator Fabric

An agentic system that cannot act on the world is just a thinking machine. The **operator fabric** is how the Agentic OS interacts with external capabilities — tools, APIs, databases, file systems, MCP servers, and any other service that produces side effects.

## Operators as Controlled Action Surfaces

In an operating system, programs interact with hardware through syscalls — controlled, typed, permissioned interfaces. The program never touches the hardware directly. The kernel mediates every interaction.

The Agentic OS applies the same principle. Agents do not call tools directly. They invoke **operators** — controlled action surfaces that:

- Have defined inputs and outputs
- Are registered and discoverable
- Are subject to governance (permissions, policies, approval flows)
- Provide isolation (failures in one operator do not crash the system)
- Are composable (operators can be chained and combined)

## Tools as Semantic Syscalls

A tool invocation in an agentic system is structurally equivalent to a syscall:

```text
OS Syscall:     write(fd, buffer, count)      → Controlled I/O
Agentic Operator: search(query, max_results)  → Controlled action
```

Both follow the same pattern: a typed interface, mediated by the kernel, subject to permissions, with structured results.

## MCP as Peripheral Subsystems

Model Context Protocol (MCP) servers are like peripheral subsystems in an OS — external devices with their own drivers and protocols. The operator fabric provides the adapter layer that:

- Discovers available MCP servers
- Translates between the kernel's internal representations and MCP protocols
- Handles connection lifecycle, errors, and retries
- Enforces governance on MCP interactions

## The Operator Registry

All available operators are registered in a central registry:

```text
Operator: file_read
  Input:  { path: string }
  Output: { content: string }
  Permissions: read
  Risk: low

Operator: database_write
  Input:  { table: string, record: object }
  Output: { id: string, success: boolean }
  Permissions: write
  Risk: medium
  Approval: required for production tables
```

The registry enables discovery, documentation, and governance. The kernel consults it when deciding which operators a worker can access.

## Composition Over Improvisation

One of the most powerful aspects of the operator fabric is composition. Rather than asking the model to improvise complex multi-step workflows, the system composes operators:

- **Operator chains** — Sequential pipelines (fetch → transform → store)
- **Operator sets** — Groups of related operators exposed as a unit
- **Skills** — Higher-level recipes that combine multiple operators with logic

Composition is more reliable than improvisation because each step is typed, tested, and governed.

## Operator Isolation

When an operator fails, the failure is contained:

- The operator's error is captured and returned as a result
- The calling process decides how to handle it (retry, fallback, escalate)
- Other operators and processes are unaffected
- The failure is logged in the execution journal

This is the same fault isolation that OS drivers provide — a bad driver should not crash the kernel.
