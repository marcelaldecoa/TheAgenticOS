# Tutorial: Coding OS

This walkthrough uses a real **To-Do API** project to demonstrate the Coding OS — fixing bugs, building features, and reviewing code with specialized agents.

## Prerequisites

- [VS Code](https://code.visualstudio.com/) with [GitHub Copilot Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat)
- Python 3.11+

## The Sample Project

The `sample-project/` folder contains a simple To-Do API:

```
sample-project/
├── src/
│   ├── __init__.py
│   ├── todo.py          # TodoStore: in-memory to-do storage
│   └── api.py           # FastAPI endpoints: CRUD for to-dos
├── tests/
│   └── test_todo.py     # Unit tests for TodoStore
└── pyproject.toml
```

**What it does**: Create, list, complete, and delete to-do items via a REST API. It's intentionally simple — and intentionally has a bug for you to fix.

## Setup

### 1. Open the workspace

Open `implementations/coding-os/` in VS Code. The `.github/` folder provides the agents and skills, and `sample-project/` is your working codebase.

### 2. Install dependencies

```bash
cd sample-project
pip install -e ".[dev]"
```

### 3. Run the tests to confirm the starting state

```bash
pytest tests/ -v
```

All 8 tests pass. The project works — but there's a bug lurking in `list_all()`.

---

## Exercise 1: Find and Fix a Bug

### The Bug

Try this in Python:

```python
from src.todo import TodoStore
store = TodoStore()
store.add("Buy milk")
store.list_all(sort="")  # Empty string — crashes with AttributeError
```

The `list_all()` method calls `getattr(t, "")` when `sort` is an empty string. The API endpoint uses `sort: str = ""` as its default, so every request to `GET /todos` without a `sort` parameter triggers this bug.

### Step 1: Use the /fix-bug skill

Open Copilot Chat and type:

```
/fix-bug The list_all method in src/todo.py crashes when sort is an empty string — getattr(t, "") raises AttributeError
```

The skill activates the 5-step workflow:

**1. Reproduce** — Copilot reads `src/todo.py`, finds `list_all`, and writes a failing test:

```python
def test_list_all_empty_sort_string(self):
    self.store.add("First")
    self.store.add("Second")
    todos = self.store.list_all(sort="")
    assert len(todos) == 2
```

**2. Diagnose** — The empty string is truthy enough to skip a falsy check in some cases, but `getattr(t, "")` always fails.

**3. Fix** — Guards the sort call:

```python
def list_all(self, sort: str = "") -> list[Todo]:
    todos = list(self._todos.values())
    if sort:
        todos.sort(key=lambda t: getattr(t, sort))
    return todos
```

**4. Verify** — Runs all tests including the new one. All pass.

**5. Document** — Summarizes: *"Root cause: empty string passed to getattr. Fixed with guard clause."*

### Step 2: Review the fix

```
@reviewer Review the changes to src/todo.py
```

The reviewer (read-only — `tools: [read, search]`) checks the fix and flags:

> **Minor**: The `sort` parameter should also validate against known field names. `sort="nonexistent"` would still crash.

### Step 3: Apply feedback

```
@coder Add validation: check that the sort field exists on Todo before using getattr
```

```
@tester Add a test for list_all with an invalid sort field name
```

**Result**: Bug fixed, edge case caught, three agents coordinated.

---

## Exercise 2: Build a New Feature

### The Feature

Add **filtering by status**: `GET /todos?status=completed` or `GET /todos?status=pending`.

### Step 1: Use the /new-feature skill

```
/new-feature Add filtering by completion status to the list endpoint. Support ?status=completed and ?status=pending.
```

### Step 2: Review the plan

Copilot produces a plan before writing code:

```
## Plan
- [ ] Read existing list_todos endpoint and TodoStore.list_all
- [ ] Add status filtering to TodoStore.list_all
- [ ] Update the API endpoint to accept a status parameter
- [ ] Write unit tests for filtering
- [ ] Review the changes
```

### Step 3: Watch the implementation

**`@coder` adds filtering to `src/todo.py`:**

```python
def list_all(self, sort: str = "", status: str = "") -> list[Todo]:
    todos = list(self._todos.values())
    if status == "completed":
        todos = [t for t in todos if t.completed]
    elif status == "pending":
        todos = [t for t in todos if not t.completed]
    if sort and hasattr(Todo, sort):
        todos.sort(key=lambda t: getattr(t, sort))
    return todos
```

**`@coder` updates `src/api.py`** — adds `status: str = ""` query parameter.

**`@tester` writes tests:**

```python
def test_filter_completed(self):
    self.store.add("Done task")
    self.store.complete(1)
    self.store.add("Pending task")
    result = self.store.list_all(status="completed")
    assert len(result) == 1
    assert result[0].completed is True

def test_filter_pending(self):
    self.store.add("Done task")
    self.store.complete(1)
    self.store.add("Pending task")
    result = self.store.list_all(status="pending")
    assert len(result) == 1
    assert result[0].completed is False
```

**`@reviewer` checks** — confirms clean implementation, consistent patterns, good test coverage.

---

## Exercise 3: Review the Whole Project

```
/code-review Review the sample-project for quality, security, and test coverage
```

The `@reviewer` reads all files and produces a severity-rated report, using the [review checklist](./github/skills/code-review/references/review-checklist.md):

```
### Major
- api.py: No validation on priority — invalid values crash with ValueError

### Minor
- Consider pagination for GET /todos at scale
- todo.py: _next_id is monotonic but not thread-safe

### Approved
- Clean separation between TodoStore and API layers
- Type hints throughout
- Tests cover core CRUD operations
```

---

## Quick Reference

| What you want | What to type |
|---|---|
| Fix a bug | `/fix-bug [description]` |
| Build a feature | `/new-feature [description]` |
| Review code | `/code-review [scope]` |
| Write code directly | `@coder [task]` |
| Write tests | `@tester [task]` |
| Review only (read-only) | `@reviewer [scope]` |

## What's Happening Under the Hood

| Copilot Primitive | Agentic OS Concept | In this tutorial |
|---|---|---|
| `copilot-instructions.md` | Cognitive Kernel | Routes tasks, sets project conventions |
| `@coder` | Coder Worker | `tools: [read, edit, search, execute]` |
| `@tester` | Tester Worker | Scoped to test files |
| `@reviewer` | Reviewer Worker | `tools: [read, search]` — **cannot edit** |
| `/fix-bug` | Bug Fix Strategy | 5-step: Reproduce → Diagnose → Fix → Verify → Document |
| `/new-feature` | Feature Strategy | Plan → Implement → Test → Review |
| `python-standards.instructions.md` | Procedural Memory | Auto-loaded for `**/*.py` files |
| `testing-standards.instructions.md` | Procedural Memory | Auto-loaded for test files |
