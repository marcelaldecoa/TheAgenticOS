# Governance Check

Verify access and audit actions through the Agent Governance Runtime.

## When to use

Use this skill whenever you need to:
- Verify your access before performing a sensitive operation
- Understand what MCPs and skills you are authorized to use
- Log audit records for compliance
- Check if an action requires human approval

## Procedure

### 1. Check your profile

Call `agr_get_profile` to see your access boundaries:
- Which MCP servers are allowed/denied
- Which actions are allowed/denied/require approval
- Your data classification level

### 2. Before side-effecting actions

For each action with side effects, follow this sequence:

```
agr_check_access(action="<action-name>")
├── ALLOWED → Proceed → agr_audit(action, result="success")
├── DENIED → Stop → agr_audit(action, result="denied") → Inform user
└── REQUIRE_APPROVAL → Ask user → if approved → Proceed → agr_audit
```

### 3. Before using external MCPs

```
agr_check_mcp(mcp_name="<server-name>")
├── ALLOWED → Use the MCP's tools normally
└── DENIED → Do not use → Inform user
```

### 4. Always audit

After every significant action, call `agr_audit` with:
- `action`: what you did
- `result`: success / failure / denied / error
- `intent`: why you did it
- `detail`: relevant context (optional)

## Examples

### Deploying to production
```
1. agr_check_access(action="deploy.production")
   → "REQUIRE_APPROVAL"
2. Ask user: "Deploying to production requires approval. Proceed?"
3. User confirms
4. Deploy
5. agr_audit(action="deploy.production", result="success",
             intent="Deploy v2.1 release", detail="Deployed to eastus2")
```

### Writing to a database
```
1. agr_check_access(action="database.write")
   → "ALLOWED"
2. Write data
3. agr_audit(action="database.write", result="success",
             intent="Update customer record", detail="customer_id=42")
```

### Using a denied MCP
```
1. agr_check_mcp(mcp_name="production-db")
   → "DENIED"
2. Inform user: "Access to production-db MCP is denied by policy."
```
