"""
FastAPI application for the To-Do API.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .todo import TodoStore

app = FastAPI(title="To-Do API", version="0.1.0")
store = TodoStore()


class TodoCreate(BaseModel):
    title: str
    priority: str = "medium"


class TodoResponse(BaseModel):
    id: int
    title: str
    completed: bool
    priority: str


@app.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(body: TodoCreate):
    todo = store.add(body.title, body.priority)
    return TodoResponse(
        id=todo.id,
        title=todo.title,
        completed=todo.completed,
        priority=todo.priority.value,
    )


@app.get("/todos", response_model=list[TodoResponse])
def list_todos(sort: str = "", status: str = ""):
    todos = store.list_all(sort, status)
    return [
        TodoResponse(
            id=t.id, title=t.title, completed=t.completed, priority=t.priority.value
        )
        for t in todos
    ]


@app.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int):
    todo = store.get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return TodoResponse(
        id=todo.id,
        title=todo.title,
        completed=todo.completed,
        priority=todo.priority.value,
    )


@app.patch("/todos/{todo_id}/complete", response_model=TodoResponse)
def complete_todo(todo_id: int):
    todo = store.complete(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return TodoResponse(
        id=todo.id,
        title=todo.title,
        completed=todo.completed,
        priority=todo.priority.value,
    )


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    if not store.delete(todo_id):
        raise HTTPException(status_code=404, detail="Todo not found")
