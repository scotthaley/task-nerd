"""Task list widget."""

from enum import Enum, auto

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Static
from textual.widgets._input import Selection

from task_nerd.models import Task, TaskStatus


class EditMode(Enum):
    """Mode for editing a task title."""

    APPEND = auto()  # 'i' - cursor at end
    INSERT = auto()  # 'I' - cursor at beginning
    SUBSTITUTE = auto()  # 's' - clear text


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


class TaskEdited(Message):
    """Message sent when a task's title is edited."""

    def __init__(self, task_id: int, new_title: str) -> None:
        self.task_id = task_id
        self.new_title = new_title
        super().__init__()


class TaskPasted(Message):
    """Message sent when a task is pasted."""

    def __init__(
        self,
        title: str,
        category: str | None,
        after_task_id: int | None,
        delete_source_id: int | None = None,
    ) -> None:
        self.title = title
        self.category = category  # From destination, not source
        self.after_task_id = after_task_id
        self.delete_source_id = delete_source_id  # For cut operation
        super().__init__()


class InputCancelled(Message):
    """Message sent when input is cancelled via Escape."""

    pass


class EscapePressedInList(Message):
    """Message sent when Escape is pressed in task list with nothing to cancel."""

    pass


class SearchSubmitted(Message):
    """Message sent when search is submitted via Enter."""

    def __init__(self, term: str) -> None:
        self.term = term
        super().__init__()


class SearchCancelled(Message):
    """Message sent when search is cancelled via Escape."""

    pass


class SearchInputRow(Horizontal):
    """An inline input row for search/filter."""

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    DEFAULT_CSS = """
    SearchInputRow {
        height: 1;
        padding: 0 1;
        width: 100%;
        background: $surface;
    }

    SearchInputRow .search-prefix {
        width: 2;
        height: 1;
    }

    SearchInputRow Input {
        border: none;
        background: transparent;
        padding: 0;
        height: 1;
        width: 1fr;
    }

    SearchInputRow Input:focus {
        border: none;
    }
    """

    def __init__(self, initial_term: str = "") -> None:
        super().__init__()
        self._initial_term = initial_term

    def compose(self) -> ComposeResult:
        yield Static("/", classes="search-prefix")
        yield Input(value=self._initial_term, id="search-input")

    def on_mount(self) -> None:
        self.call_later(self._focus_input)

    def _focus_input(self) -> None:
        input_widget = self.query_one(Input)
        input_widget.focus()
        input_widget.cursor_position = len(input_widget.value)

    def action_cancel(self) -> None:
        """Handle Escape key - exit search mode."""
        self.post_message(SearchCancelled())


class CategoryRow(Static):
    """A non-selectable header row for a category group."""

    DEFAULT_CSS = """
    CategoryRow {
        height: auto;
        padding: 1 1 0 1;
    }

    CategoryRow Static {
        text-style: bold;
    }
    """

    def __init__(self, category_name: str) -> None:
        super().__init__(f"# {category_name}")
        self.add_class("category-header")


class TaskRow(Static):
    """A single task row display."""

    DEFAULT_CSS = """
    TaskRow {
        height: auto;
        padding: 0 1;
        border-left: none;
    }

    TaskRow.-completed {
        text-style: strike;
        color: $text-muted;
    }

    TaskRow.-copied {
        border-left: wide $success;
    }

    TaskRow.-cut {
        border-left: wide $warning;
    }
    """

    def __init__(self, task: Task, indented: bool = False) -> None:
        self.task_id = task.id
        self.task_data = task
        self._indented = indented
        status_indicator = self._get_status_indicator(task.status)
        prefix = "  " if indented else ""
        super().__init__(f"{prefix}{status_indicator} {task.title}")

        if task.status == TaskStatus.COMPLETED:
            self.add_class("-completed")
        if indented:
            self.add_class("-indented")

    def _get_status_indicator(self, status: TaskStatus) -> str:
        # Backslash escapes brackets to prevent Rich markup interpretation
        indicators = {
            TaskStatus.PENDING: r"\[ ]",
            TaskStatus.IN_PROGRESS: r"\[~]",
            TaskStatus.COMPLETED: r"\[x]",
            TaskStatus.CANCELLED: r"\[-]",
        }
        return indicators.get(status, r"\[ ]")


class NewTaskInputRow(Horizontal):
    """An inline input row for creating a new task."""

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    DEFAULT_CSS = """
    NewTaskInputRow {
        height: 1;
        padding: 0 1;
        width: 100%;
    }

    NewTaskInputRow .status-prefix {
        width: 4;
        height: 1;
    }

    NewTaskInputRow .indent-prefix {
        width: 2;
        height: 1;
    }

    NewTaskInputRow Input {
        border: none;
        background: transparent;
        padding: 0;
        height: 1;
        width: 1fr;
    }

    NewTaskInputRow Input:focus {
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
        if self._indented:
            yield Static("  ", classes="indent-prefix")
        yield Static(r"\[ ] ", classes="status-prefix")
        yield Input(id="new-task-input")

    def on_mount(self) -> None:
        self.call_later(self._focus_input)

    def _focus_input(self) -> None:
        self.query_one(Input).focus()

    def action_cancel(self) -> None:
        """Handle Escape key - cancel new task creation."""
        self.post_message(InputCancelled())


class EditTaskInputRow(Horizontal):
    """An inline input row for editing an existing task."""

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    DEFAULT_CSS = """
    EditTaskInputRow {
        height: 1;
        padding: 0 1;
        width: 100%;
    }

    EditTaskInputRow .status-prefix {
        width: 4;
        height: 1;
    }

    EditTaskInputRow .indent-prefix {
        width: 2;
        height: 1;
    }

    EditTaskInputRow Input {
        border: none;
        background: transparent;
        padding: 0;
        height: 1;
        width: 1fr;
    }

    EditTaskInputRow Input:focus {
        border: none;
    }
    """

    def __init__(self, task: Task, edit_mode: EditMode, indented: bool = False) -> None:
        super().__init__()
        self.task_data = task
        self._edit_mode = edit_mode
        self._indented = indented

    @property
    def task_id(self) -> int:
        """Return the ID of the task being edited."""
        return self.task_data.id

    def compose(self) -> ComposeResult:
        initial_value = (
            "" if self._edit_mode == EditMode.SUBSTITUTE else self.task_data.title
        )

        if self._indented:
            yield Static("  ", classes="indent-prefix")
        yield Static(
            self._get_status_indicator(self.task_data.status), classes="status-prefix"
        )
        yield Input(value=initial_value, id="edit-task-input", select_on_focus=False)

    def _get_status_indicator(self, status: TaskStatus) -> str:
        # Backslash escapes brackets to prevent Rich markup interpretation
        indicators = {
            TaskStatus.PENDING: r"\[ ] ",
            TaskStatus.IN_PROGRESS: r"\[~] ",
            TaskStatus.COMPLETED: r"\[x] ",
            TaskStatus.CANCELLED: r"\[-] ",
        }
        return indicators.get(status, r"\[ ] ")

    def on_mount(self) -> None:
        self.call_later(self._focus_input)

    def _focus_input(self) -> None:
        input_widget = self.query_one(Input)
        input_widget.focus()
        if self._edit_mode == EditMode.INSERT:
            cursor_pos = 0
        else:
            cursor_pos = len(input_widget.value)
        input_widget.cursor_position = cursor_pos
        input_widget.selection = Selection.cursor(cursor_pos)

    def action_cancel(self) -> None:
        """Handle Escape key - cancel edit."""
        self.post_message(InputCancelled())


class SimpleTaskList(VerticalScroll, can_focus=True, can_focus_children=False):
    """Custom task list widget with task ID-based selection."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("space", "toggle_status", "Toggle done", show=True),
        Binding("a", "edit_append", "Edit", show=False),
        Binding("i", "edit_append", "Edit", show=True),
        Binding("I", "edit_insert", "Edit (start)", show=False),
        Binding("s", "edit_substitute", "Replace", show=False),
        Binding("d", "delete_press", "Delete", show=True),
        Binding("escape", "cancel_delete", "Cancel", show=False),
        Binding("y", "copy_task", "Copy", show=False),
        Binding("x", "cut_task", "Cut", show=False),
        Binding("p", "paste_task", "Paste", show=False),
    ]

    DEFAULT_CSS = """
    SimpleTaskList {
        height: 1fr;
    }

    SimpleTaskList:focus TaskRow.-selected {
        background: $accent;
        color: $text;
    }

    SimpleTaskList TaskRow.-selected {
        background: $surface;
        color: $text;
    }
    """

    selected_task_id: reactive[int | None] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._task_ids: list[int] = []
        self._delete_pending: bool = False
        self._clipboard_task: Task | None = None
        self._clipboard_mode: str | None = None  # "copy" or "cut"
        self._clipboard_ready: bool = False  # Prevent clipboard ops until user interaction

    def watch_selected_task_id(self, old_id: int | None, new_id: int | None) -> None:
        """Update CSS classes when selection changes."""
        if old_id is not None:
            try:
                old_row = self.query_one(f"TaskRow#task-{old_id}", TaskRow)
                old_row.remove_class("-selected")
            except Exception:
                pass

        if new_id is not None:
            try:
                new_row = self.query_one(f"TaskRow#task-{new_id}", TaskRow)
                new_row.add_class("-selected")
                new_row.scroll_visible()
            except Exception:
                pass

    def get_selected_task(self) -> Task | None:
        """Return the currently selected task, or None if no task is selected."""
        if self.selected_task_id is None:
            return None
        try:
            row = self.query_one(f"TaskRow#task-{self.selected_task_id}", TaskRow)
            return row.task_data
        except Exception:
            return None

    def get_selected_task_row(self) -> TaskRow | None:
        """Return the currently selected TaskRow, or None if none selected."""
        if self.selected_task_id is None:
            return None
        try:
            return self.query_one(f"TaskRow#task-{self.selected_task_id}", TaskRow)
        except Exception:
            return None

    def action_cursor_down(self) -> None:
        """Move selection to next task."""
        self._clipboard_ready = True  # User has interacted
        if not self._task_ids:
            return
        if self.selected_task_id is None:
            self.selected_task_id = self._task_ids[0]
        else:
            try:
                idx = self._task_ids.index(self.selected_task_id)
                if idx < len(self._task_ids) - 1:
                    self.selected_task_id = self._task_ids[idx + 1]
            except ValueError:
                self.selected_task_id = self._task_ids[0] if self._task_ids else None

    def action_cursor_up(self) -> None:
        """Move selection to previous task."""
        self._clipboard_ready = True  # User has interacted
        if not self._task_ids:
            return
        if self.selected_task_id is None:
            self.selected_task_id = self._task_ids[-1]
        else:
            try:
                idx = self._task_ids.index(self.selected_task_id)
                if idx > 0:
                    self.selected_task_id = self._task_ids[idx - 1]
            except ValueError:
                self.selected_task_id = self._task_ids[-1] if self._task_ids else None

    def action_toggle_status(self) -> None:
        """Toggle the selected task between done and not done."""
        self._clipboard_ready = True  # User has interacted
        task = self.get_selected_task()
        if task is not None:
            new_status = (
                TaskStatus.PENDING
                if task.status == TaskStatus.COMPLETED
                else TaskStatus.COMPLETED
            )
            self.post_message(TaskStatusToggled(task.id, new_status))

    def action_delete_press(self) -> None:
        """Handle 'd' key press for vim-style delete."""
        self._clipboard_ready = True  # User has interacted
        if self.selected_task_id is None:
            return

        if not self._delete_pending:
            self._delete_pending = True
            self.post_message(
                StatusBarUpdate("Press d again to delete, Escape to cancel")
            )
        else:
            self._delete_pending = False
            self.post_message(StatusBarUpdate(""))
            self.post_message(TaskDeleted(self.selected_task_id))

    def action_cancel_delete(self) -> None:
        """Cancel pending delete, clear clipboard, or notify app of escape press."""
        if self._delete_pending:
            self._delete_pending = False
            self.post_message(StatusBarUpdate(""))
        elif self._clipboard_task is not None:
            self._clipboard_task = None
            self._clipboard_mode = None
            self._clear_clipboard_styling()
            self.post_message(StatusBarUpdate(""))
        else:
            # Nothing to cancel locally, let the app handle it
            self.post_message(EscapePressedInList())

    def action_edit_append(self) -> None:
        """Edit task with cursor at end (append mode)."""
        self._clipboard_ready = True  # User has interacted
        self._start_edit(EditMode.APPEND)

    def action_edit_insert(self) -> None:
        """Edit task with cursor at beginning (insert mode)."""
        self._clipboard_ready = True  # User has interacted
        self._start_edit(EditMode.INSERT)

    def action_edit_substitute(self) -> None:
        """Edit task with text cleared (substitute mode)."""
        self._clipboard_ready = True  # User has interacted
        self._start_edit(EditMode.SUBSTITUTE)

    def _start_edit(self, mode: EditMode) -> None:
        """Start editing the selected task."""
        task_row = self.get_selected_task_row()
        if task_row is None:
            return
        task_list_view = self.parent
        if isinstance(task_list_view, TaskListView):
            task_list_view.start_edit(task_row, mode)

    def _clear_clipboard_styling(self) -> None:
        """Remove clipboard styling from all task rows."""
        for row in self.query(TaskRow):
            row.remove_class("-copied")
            row.remove_class("-cut")

    def action_copy_task(self) -> None:
        """Copy the selected task to clipboard."""
        if not self._clipboard_ready:
            return
        task = self.get_selected_task()
        if task is None:
            return

        self._clipboard_task = task
        self._clipboard_mode = "copy"

        self._clear_clipboard_styling()
        task_row = self.get_selected_task_row()
        if task_row:
            task_row.add_class("-copied")

        self.post_message(StatusBarUpdate("Task copied"))

    def action_cut_task(self) -> None:
        """Cut the selected task to clipboard."""
        if not self._clipboard_ready:
            return
        task = self.get_selected_task()
        if task is None:
            return

        self._clipboard_task = task
        self._clipboard_mode = "cut"

        self._clear_clipboard_styling()
        task_row = self.get_selected_task_row()
        if task_row:
            task_row.add_class("-cut")

        self.post_message(StatusBarUpdate("Task cut"))

    def action_paste_task(self) -> None:
        """Paste the clipboard task after the selected task."""
        if not self._clipboard_ready:
            return
        if self._clipboard_task is None:
            return

        selected_task = self.get_selected_task()
        after_task_id = selected_task.id if selected_task else None
        category = selected_task.category if selected_task else None

        delete_source_id = (
            self._clipboard_task.id if self._clipboard_mode == "cut" else None
        )

        self.post_message(
            TaskPasted(
                title=self._clipboard_task.title,
                category=category,
                after_task_id=after_task_id,
                delete_source_id=delete_source_id,
            )
        )

        if self._clipboard_mode == "cut":
            self._clipboard_task = None
            self._clipboard_mode = None
            self._clear_clipboard_styling()

    def clear_clipboard_if_deleted(self, task_id: int) -> None:
        """Clear clipboard if the source task was deleted."""
        if self._clipboard_task and self._clipboard_task.id == task_id:
            self._clipboard_task = None
            self._clipboard_mode = None

    def apply_clipboard_styling(self) -> None:
        """Re-apply clipboard styling to the correct row after refresh."""
        if self._clipboard_task is None:
            return
        try:
            row = self.query_one(f"TaskRow#task-{self._clipboard_task.id}", TaskRow)
            if self._clipboard_mode == "copy":
                row.add_class("-copied")
            elif self._clipboard_mode == "cut":
                row.add_class("-cut")
        except Exception:
            pass


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
        self._editing_task_row: TaskRow | None = None
        self._is_filtered = False

    def compose(self) -> ComposeResult:
        yield Vertical(id="input-container")
        yield SimpleTaskList(id="task-list")

    def load_tasks(
        self,
        tasks: list[Task],
        select_task_id: int | None = None,
        is_filtered: bool = False,
        focus_list: bool = True,
    ) -> None:
        """Load tasks into the list view.

        Args:
            tasks: List of tasks to display.
            select_task_id: If provided, select this task after loading.
            is_filtered: If True, show "No matching tasks" when empty.
            focus_list: If True, focus the task list after loading.
        """
        self._tasks = tasks
        self._is_filtered = is_filtered
        self._refresh_list(select_task_id=select_task_id, focus_list=focus_list)

    def _refresh_list(
        self, select_task_id: int | None = None, focus_list: bool = True
    ) -> None:
        """Refresh the task list with current tasks.

        Args:
            select_task_id: If provided, select this task after rebuilding the list.
            focus_list: If True, focus the task list after refreshing.
        """
        task_list = self.query_one("#task-list", SimpleTaskList)

        # Temporarily set to None to avoid triggering watch on old ID
        task_list._reactive_selected_task_id = None

        # Remove all children - await will complete the removal before continuing
        task_list.remove_children()

        # Capture focus_list in closure
        should_focus = focus_list

        def do_mount() -> None:
            tl = self.query_one("#task-list", SimpleTaskList)
            tl._task_ids = []

            if not self._tasks and not self._editing:
                try:
                    self.query_one("#empty-message")
                except Exception:
                    empty_text = (
                        "No matching tasks."
                        if self._is_filtered
                        else "No tasks yet. Press 'a' to add one."
                    )
                    self.mount(Static(empty_text, id="empty-message"))
            else:
                try:
                    empty_msg = self.query_one("#empty-message")
                    empty_msg.remove()
                except Exception:
                    pass

                current_category: str | None = None
                for task in self._tasks:
                    if task.category != current_category:
                        current_category = task.category
                        if current_category is not None:
                            tl.mount(CategoryRow(current_category))

                    indented = task.category is not None
                    row = TaskRow(task, indented=indented)
                    row.id = f"task-{task.id}"
                    tl.mount(row)
                    tl._task_ids.append(task.id)

            # Set selection
            if select_task_id is not None and select_task_id in tl._task_ids:
                tl.selected_task_id = select_task_id
            elif tl._task_ids:
                tl.selected_task_id = tl._task_ids[0]
            else:
                tl.selected_task_id = None

            # Re-apply clipboard styling after refresh
            tl.apply_clipboard_styling()

            if should_focus:
                tl.focus()

        self.call_after_refresh(do_mount)

    def show_input(self) -> None:
        """Show an inline input row after the selected task."""
        if self._editing:
            return
        self._editing = True

        try:
            empty_msg = self.query_one("#empty-message")
            empty_msg.remove()
        except Exception:
            pass

        task_list = self.query_one("#task-list", SimpleTaskList)
        selected_task = task_list.get_selected_task()

        default_category: str | None = None
        after_task_id: int | None = None
        indented = False

        if selected_task is not None:
            default_category = selected_task.category
            after_task_id = selected_task.id
            indented = selected_task.category is not None

        new_row = NewTaskInputRow(
            default_category=default_category,
            after_task_id=after_task_id,
            indented=indented,
        )

        selected_row = task_list.get_selected_task_row()
        if selected_row is not None:
            task_list.mount(new_row, after=selected_row)
        else:
            if task_list.children:
                task_list.mount(new_row)
            else:
                input_container = self.query_one("#input-container", Vertical)
                input_container.mount(new_row)

    def hide_input(self) -> None:
        """Remove the inline input row for new tasks."""
        if not self._editing:
            return
        self._editing = False

        task_list = self.query_one("#task-list", SimpleTaskList)
        task_id_to_restore = task_list.selected_task_id

        try:
            new_task_row = self.query_one(NewTaskInputRow)
            new_task_row.remove()
        except Exception:
            pass

        self._refresh_list(select_task_id=task_id_to_restore)

    def start_edit(self, task_row: TaskRow, mode: EditMode) -> None:
        """Replace the task row with an edit row."""
        if self._editing:
            return
        self._editing = True
        self._editing_task_row = task_row

        task = task_row.task_data
        indented = task.category is not None
        edit_row = EditTaskInputRow(task, mode, indented=indented)

        task_list = self.query_one("#task-list", SimpleTaskList)
        task_list.mount(edit_row, after=task_row)
        task_row.remove()

    def hide_edit(self) -> None:
        """Remove the edit row and restore the task list."""
        if not self._editing:
            return
        self._editing = False
        self._editing_task_row = None

        task_list = self.query_one("#task-list", SimpleTaskList)
        task_id_to_restore = task_list.selected_task_id

        self._refresh_list(select_task_id=task_id_to_restore)

    def focus_list(self) -> None:
        """Focus the task list for keyboard navigation."""
        self.query_one("#task-list", SimpleTaskList).focus()

    def select_task_by_id(self, task_id: int | None) -> None:
        """Select a task by its ID."""
        if task_id is None:
            return
        task_list = self.query_one("#task-list", SimpleTaskList)
        if task_id in task_list._task_ids:
            task_list.selected_task_id = task_id

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "new-task-input" and event.value.strip():
            try:
                new_task_row = self.query_one(NewTaskInputRow)
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
            try:
                new_task_row = self.query_one(NewTaskInputRow)
                new_task_row.remove()
            except Exception:
                pass
        elif event.input.id == "edit-task-input" and event.value.strip():
            try:
                edit_row = self.query_one(EditTaskInputRow)
                task_id = edit_row.task_id
            except Exception:
                return

            self.post_message(TaskEdited(task_id, event.value.strip()))
            self._editing = False
            self._editing_task_row = None
            try:
                edit_row = self.query_one(EditTaskInputRow)
                edit_row.remove()
            except Exception:
                pass

    def on_input_cancelled(self, event: InputCancelled) -> None:
        """Handle input cancellation via Escape."""
        self.hide_edit()
        self.hide_input()
