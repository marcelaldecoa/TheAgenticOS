"""
To-Do API — A simple task management application.
Used as the sample project for the Coding OS tutorial.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Todo:
    id: int
    title: str
    completed: bool = False
    priority: Priority = Priority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)


class TodoStore:
    """In-memory to-do storage."""

    def __init__(self):
        self._todos: dict[int, Todo] = {}
        self._next_id: int = 1

    def add(self, title: str, priority: str = "medium") -> Todo:
        """Create a new to-do item."""
        todo = Todo(
            id=self._next_id,
            title=title,
            priority=Priority(priority),
        )
        self._todos[todo.id] = todo
        self._next_id += 1
        return todo

    def get(self, todo_id: int) -> Todo | None:
        """Get a to-do by ID."""
        return self._todos.get(todo_id)

    def list_all(self, sort: str = "") -> list[Todo]:
        """List all to-dos, optionally sorted by a field."""
        todos = list(self._todos.values())
        if sort:
            todos.sort(key=lambda t: getattr(t, sort))
        return todos

    def complete(self, todo_id: int) -> Todo | None:
        """Mark a to-do as completed."""
        todo = self._todos.get(todo_id)
        if todo:
            todo.completed = True
        return todo

    def delete(self, todo_id: int) -> bool:
        """Delete a to-do by ID."""
        if todo_id in self._todos:
            del self._todos[todo_id]
            return True
        return False
