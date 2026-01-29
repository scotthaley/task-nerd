"""Task list widget."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, ListItem, ListView, Static

from task_nerd.models import Task, TaskStatus


class TaskCreated(Message):
    """Message sent when a new task is created."""

    def __init__(self, title: str) -> None:
        self.title = title
        super().__init__()


class TaskStatusToggled(Message):
    """Message sent when a task's status is toggled."""

    def __init__(self, task_id: int, new_status: TaskStatus) -> None:
        self.task_id = task_id
        self.new_status = new_status
        super().__init__()


class CategoryHeader(ListItem):
    """A non-selectable header row for a category group."""

    def __init__(self, category_name: str) -> None:
        self._category_name = category_name
        super().__init__()
        self.disabled = True

    def compose(self) -> ComposeResult:
        yield Static(f"# {self._category_name}")


class TaskListItem(ListItem):
    """A single task row display as a ListItem."""

    def __init__(self, task: Task, indented: bool = False) -> None:
        self._task_data = task
        self._indented = indented
        super().__init__()
        if task.status == TaskStatus.COMPLETED:
            self.add_class("-completed")
        if indented:
            self.add_class("-indented")

    def compose(self) -> ComposeResult:
        status_indicator = self._get_status_indicator(self._task_data.status)
        prefix = "  " if self._indented else ""
        yield Static(f"{prefix}{status_indicator} {self._task_data.title}")

    def _get_status_indicator(self, status: TaskStatus) -> str:
        indicators = {
            TaskStatus.PENDING: "[ ]",
            TaskStatus.IN_PROGRESS: "[~]",
            TaskStatus.COMPLETED: "[x]",
            TaskStatus.CANCELLED: "[-]",
        }
        return indicators.get(status, "[ ]")


class NewTaskRow(Horizontal):
    """An inline input row for creating a new task."""

    DEFAULT_CSS = """
    NewTaskRow {
        height: auto;
        width: 100%;
        padding: 0 1;
    }

    NewTaskRow .status-prefix {
        width: 4;
    }

    NewTaskRow Input {
        border: none;
        background: transparent;
        padding: 0;
        height: 1;
        width: 1fr;
    }

    NewTaskRow Input:focus {
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[ ] ", classes="status-prefix")
        yield Input(id="new-task-input")

    def on_mount(self) -> None:
        self.query_one(Input).focus()


class TaskList(ListView):
    """ListView for displaying tasks with j/k navigation."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("space", "toggle_status", "Toggle done", show=True),
    ]

    DEFAULT_CSS = """
    TaskList {
        height: 1fr;
    }

    TaskList:focus > TaskListItem.-highlight {
        background: $accent;
    }

    TaskList > TaskListItem.-highlight {
        background: $surface;
    }

    TaskList > TaskListItem {
        height: auto;
        padding: 0 1;
    }

    TaskList > TaskListItem.-completed Static {
        text-style: strike;
        color: $text-muted;
    }

    TaskList > CategoryHeader {
        height: auto;
        padding: 1 1 0 1;
    }

    TaskList > CategoryHeader Static {
        text-style: bold;
    }
    """

    def action_toggle_status(self) -> None:
        """Toggle the highlighted task between done and not done."""
        if self.highlighted_child and isinstance(self.highlighted_child, TaskListItem):
            task = self.highlighted_child._task_data
            new_status = TaskStatus.PENDING if task.status == TaskStatus.COMPLETED else TaskStatus.COMPLETED
            self.post_message(TaskStatusToggled(task.id, new_status))


class TaskListView(Vertical):
    """Widget displaying a list of tasks with inline creation."""

    DEFAULT_CSS = """
    TaskListView {
        height: 1fr;
    }

    TaskListView #input-container {
        height: auto;
    }

    TaskListView #empty-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[Task] = []
        self._editing = False

    def compose(self) -> ComposeResult:
        yield Vertical(id="input-container")
        yield TaskList(id="task-list")

    def load_tasks(self, tasks: list[Task]) -> None:
        """Load tasks into the list view."""
        self._tasks = tasks
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Refresh the task list with current tasks."""
        task_list = self.query_one("#task-list", TaskList)
        task_list.clear()

        if not self._tasks and not self._editing:
            # Show empty message - mount it outside the list
            try:
                self.query_one("#empty-message")
            except Exception:
                self.mount(Static("No tasks yet. Press 'a' to add one.", id="empty-message"))
        else:
            # Remove empty message if present
            try:
                empty_msg = self.query_one("#empty-message")
                empty_msg.remove()
            except Exception:
                pass

            current_category: str | None = None
            for task in self._tasks:
                # Insert category header when category changes
                if task.category != current_category:
                    current_category = task.category
                    if current_category is not None:
                        task_list.append(CategoryHeader(current_category))

                # Tasks with a category are indented
                indented = task.category is not None
                task_list.append(TaskListItem(task, indented=indented))

    def show_input(self) -> None:
        """Show an inline input row at the top of the list."""
        if self._editing:
            return
        self._editing = True

        # Remove empty message if present
        try:
            empty_msg = self.query_one("#empty-message")
            empty_msg.remove()
        except Exception:
            pass

        input_container = self.query_one("#input-container", Vertical)
        input_container.mount(NewTaskRow())

    def hide_input(self) -> None:
        """Remove the inline input row."""
        if not self._editing:
            return
        self._editing = False
        try:
            new_task_row = self.query_one(NewTaskRow)
            new_task_row.remove()
        except Exception:
            pass
        self._refresh_list()

    def focus_list(self) -> None:
        """Focus the task list for keyboard navigation."""
        self.query_one("#task-list", TaskList).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "new-task-input" and event.value.strip():
            self.post_message(TaskCreated(event.value.strip()))
            self._editing = False
            # Remove the input row
            try:
                new_task_row = self.query_one(NewTaskRow)
                new_task_row.remove()
            except Exception:
                pass
