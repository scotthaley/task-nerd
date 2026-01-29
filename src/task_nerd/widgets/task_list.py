"""Task list widget."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, ListItem, ListView, Static

from task_nerd.models import Task, TaskStatus


class TaskCreated(Message):
    """Message sent when a new task is created."""

    def __init__(
        self,
        title: str,
        default_category: str | None = None,
        after_task_id: int | None = None,
    ) -> None:
        self.title = title
        self.default_category = default_category
        self.after_task_id = after_task_id
        super().__init__()


class TaskStatusToggled(Message):
    """Message sent when a task's status is toggled."""

    def __init__(self, task_id: int, new_status: TaskStatus) -> None:
        self.task_id = task_id
        self.new_status = new_status
        super().__init__()


class TaskDeleted(Message):
    """Message sent when a task is deleted."""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__()


class StatusBarUpdate(Message):
    """Message sent to update the status bar text."""

    def __init__(self, text: str) -> None:
        self.text = text
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


class NewTaskRow(ListItem):
    """An inline input row for creating a new task."""

    DEFAULT_CSS = """
    NewTaskRow {
        height: 1;
        padding: 0 1;
    }

    NewTaskRow Horizontal {
        height: 1;
        width: 100%;
    }

    NewTaskRow .status-prefix {
        width: 4;
        height: 1;
    }

    NewTaskRow .indent-prefix {
        width: 2;
        height: 1;
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

    def __init__(
        self,
        default_category: str | None = None,
        after_task_id: int | None = None,
        indented: bool = False,
    ) -> None:
        super().__init__()
        self.default_category = default_category
        self.after_task_id = after_task_id
        self._indented = indented

    def compose(self) -> ComposeResult:
        with Horizontal():
            if self._indented:
                yield Static("  ", classes="indent-prefix")
            yield Static("[ ] ", classes="status-prefix")
            yield Input(id="new-task-input")

    def on_mount(self) -> None:
        # Use call_later to ensure the widget tree is fully ready before focusing
        self.call_later(self._focus_input)

    def _focus_input(self) -> None:
        self.query_one(Input).focus()


class TaskList(ListView):
    """ListView for displaying tasks with j/k navigation."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("space", "toggle_status", "Toggle done", show=True),
        Binding("d", "delete_press", "Delete", show=True),
        Binding("escape", "cancel_delete", "Cancel", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._delete_pending: bool = False

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

    TaskList > NewTaskRow {
        height: 1;
        padding: 0 1;
    }
    """

    def action_toggle_status(self) -> None:
        """Toggle the highlighted task between done and not done."""
        if self.highlighted_child and isinstance(self.highlighted_child, TaskListItem):
            task = self.highlighted_child._task_data
            new_status = TaskStatus.PENDING if task.status == TaskStatus.COMPLETED else TaskStatus.COMPLETED
            self.post_message(TaskStatusToggled(task.id, new_status))

    def action_delete_press(self) -> None:
        """Handle 'd' key press for vim-style delete."""
        if not self.highlighted_child or not isinstance(self.highlighted_child, TaskListItem):
            return

        if not self._delete_pending:
            self._delete_pending = True
            self.post_message(StatusBarUpdate("Press d again to delete, Escape to cancel"))
        else:
            task = self.highlighted_child._task_data
            self._delete_pending = False
            self.post_message(StatusBarUpdate(""))
            self.post_message(TaskDeleted(task.id))

    def action_cancel_delete(self) -> None:
        """Cancel pending delete operation."""
        if self._delete_pending:
            self._delete_pending = False
            self.post_message(StatusBarUpdate(""))

    def get_selected_task(self) -> Task | None:
        """Return the currently highlighted task, or None if no task is selected."""
        if self.highlighted_child and isinstance(self.highlighted_child, TaskListItem):
            return self.highlighted_child._task_data
        return None


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
        """Show an inline input row after the selected task."""
        if self._editing:
            return
        self._editing = True

        # Remove empty message if present
        try:
            empty_msg = self.query_one("#empty-message")
            empty_msg.remove()
        except Exception:
            pass

        task_list = self.query_one("#task-list", TaskList)
        selected_task = task_list.get_selected_task()

        # Determine category and position context
        default_category: str | None = None
        after_task_id: int | None = None
        indented = False

        if selected_task is not None:
            default_category = selected_task.category
            after_task_id = selected_task.id
            indented = selected_task.category is not None

        new_row = NewTaskRow(
            default_category=default_category,
            after_task_id=after_task_id,
            indented=indented,
        )

        # Mount the input row
        if task_list.highlighted_child is not None:
            task_list.mount(new_row, after=task_list.highlighted_child)
        else:
            # No selection - append at end of list or use input container if empty
            if task_list.children:
                task_list.mount(new_row)
            else:
                input_container = self.query_one("#input-container", Vertical)
                input_container.mount(new_row)

    def hide_input(self) -> None:
        """Remove the inline input row."""
        if not self._editing:
            return
        self._editing = False
        try:
            # Query from entire TaskListView since NewTaskRow could be in TaskList or input-container
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
            # Get context from the NewTaskRow
            try:
                new_task_row = self.query_one(NewTaskRow)
                default_category = new_task_row.default_category
                after_task_id = new_task_row.after_task_id
            except Exception:
                default_category = None
                after_task_id = None

            self.post_message(
                TaskCreated(
                    event.value.strip(),
                    default_category=default_category,
                    after_task_id=after_task_id,
                )
            )
            self._editing = False
            # Remove the input row
            try:
                new_task_row = self.query_one(NewTaskRow)
                new_task_row.remove()
            except Exception:
                pass
