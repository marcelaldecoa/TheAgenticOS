from src.todo import TodoStore


class TestTodoStore:
    def setup_method(self):
        self.store = TodoStore()

    def test_add_todo(self):
        todo = self.store.add("Buy milk")
        assert todo.id == 1
        assert todo.title == "Buy milk"
        assert todo.completed is False

    def test_add_todo_with_priority(self):
        todo = self.store.add("Fix server", priority="high")
        assert todo.priority.value == "high"

    def test_get_todo(self):
        self.store.add("Test item")
        todo = self.store.get(1)
        assert todo is not None
        assert todo.title == "Test item"

    def test_get_nonexistent_todo(self):
        result = self.store.get(999)
        assert result is None

    def test_list_all(self):
        self.store.add("First")
        self.store.add("Second")
        todos = self.store.list_all()
        assert len(todos) == 2

    def test_list_all_empty_sort_string(self):
        self.store.add("First")
        self.store.add("Second")
        todos = self.store.list_all(sort="")
        assert len(todos) == 2

    def test_list_all_invalid_sort_field(self):
        self.store.add("First")
        todos = self.store.list_all(sort="nonexistent")
        assert len(todos) == 1

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

    def test_complete_todo(self):
        self.store.add("Finish report")
        todo = self.store.complete(1)
        assert todo.completed is True

    def test_delete_todo(self):
        self.store.add("Temporary")
        assert self.store.delete(1) is True
        assert self.store.get(1) is None

    def test_delete_nonexistent(self):
        assert self.store.delete(999) is False
