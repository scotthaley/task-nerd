"""Main application module."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from task_nerd.database import Database
from task_nerd.models import TaskStatus
from task_nerd.screens import CreateDatabaseDialog
from task_nerd.utils import parse_task_title
from task_nerd.widgets import TaskListView
from task_nerd.widgets.task_list import (
    SimpleTaskList,
    StatusBarUpdate,
    TaskCreated,
    TaskDeleted,
    TaskEdited,
    TaskStatusToggled,
)


class TaskNerdApp(App):
    """A Textual app for task-nerd."""

    hide_completed: reactive[bool] = reactive(False, bindings=True)

    BINDINGS = [
        ("a", "add_task", "Add task"),
        ("escape", "cancel_input", "Cancel"),
        Binding("f1", "hide_completed_tasks", "Hide done"),
        Binding("f1", "show_completed_tasks", "Show done"),
        ("D", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Control which F1 binding is shown based on current state."""
        if action == "hide_completed_tasks":
            return not self.hide_completed
        if action == "show_completed_tasks":
            return self.hide_completed
        return True

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self.db_path = Path.cwd() / "tasks.db"
        self.database: Database | None = None

    CSS = """
    #status-bar {
        height: 1;
        width: 100%;
        background: $surface;
        color: $warning;
        padding: 0 1;
    }

    #status-bar.hidden {
        display: none;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield TaskListView()
        yield Static("", id="status-bar", classes="hidden")
        yield Footer()

    def on_mount(self) -> None:
        """Handle application mount - check for database."""
        self.theme = "catppuccin-mocha"

        if not self.db_path.exists():
            self.push_screen(CreateDatabaseDialog(self.db_path), self._on_dialog_result)
        else:
            self._initialize_database()

    def _on_dialog_result(self, result: bool) -> None:
        """Handle the result from CreateDatabaseDialog."""
        if result:
            self._create_database()
        else:
            self.exit()

    def _create_database(self) -> None:
        """Create a new database and initialize schema."""
        try:
            self.database = Database(self.db_path)
            self.database.initialize_schema()
            self._load_tasks()
        except PermissionError:
            self.notify(
                f"Permission denied: Cannot create database at {self.db_path}",
                severity="error",
            )
            self.exit()
        except Exception as e:
            self.notify(f"Failed to create database: {e}", severity="error")
            self.exit()

    def _initialize_database(self) -> None:
        """Connect to existing database and verify it."""
        try:
            self.database = Database(self.db_path)
            if not self.database.verify_connection():
                self.notify(
                    "Database appears corrupted. Consider removing tasks.db and restarting.",
                    severity="error",
                )
                self.exit()
                return

            version = self.database.get_schema_version()
            if version is None:
                # Old database without version table - initialize schema
                self.database.initialize_schema()
            else:
                # Run any pending migrations
                self.database.migrate_schema()
            self._load_tasks()
        except PermissionError:
            self.notify(
                f"Permission denied: Cannot read database at {self.db_path}",
                severity="error",
            )
            self.exit()
        except Exception as e:
            self.notify(f"Failed to open database: {e}", severity="error")
            self.exit()

    def _load_tasks(self, select_task_id: int | None = None) -> None:
        """Load tasks from database into the task list view.

        Args:
            select_task_id: If provided, select this task after loading.
        """
        if self.database:
            tasks = self.database.get_all_tasks()
            if self.hide_completed:
                tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
            task_list_view = self.query_one(TaskListView)
            task_list_view.load_tasks(tasks, select_task_id=select_task_id)
            task_list_view.focus_list()

    def action_hide_completed_tasks(self) -> None:
        """Hide completed tasks from the list."""
        self.hide_completed = True
        self._refresh_after_hide_toggle()

    def action_show_completed_tasks(self) -> None:
        """Show completed tasks in the list."""
        self.hide_completed = False
        self._refresh_after_hide_toggle()

    def _refresh_after_hide_toggle(self) -> None:
        """Refresh the task list after toggling hide completed state."""
        task_list = self.query_one(TaskListView).query_one("#task-list", SimpleTaskList)
        self._load_tasks(select_task_id=task_list.selected_task_id)

    def action_add_task(self) -> None:
        """Show the task input field."""
        self.query_one(TaskListView).show_input()

    def action_cancel_input(self) -> None:
        """Hide the task input field or edit row."""
        task_list_view = self.query_one(TaskListView)
        task_list_view.hide_input()
        task_list_view.hide_edit()

    def on_task_created(self, event: TaskCreated) -> None:
        """Handle task creation from the task list widget."""
        if self.database:
            task_list_view = self.query_one(TaskListView)
            task_list_view.hide_input()
            title, explicit_category = parse_task_title(event.title)
            category = (
                explicit_category
                if explicit_category is not None
                else event.default_category
            )
            new_task = self.database.create_task_at_position(
                title, category, event.after_task_id
            )
            self._load_tasks(select_task_id=new_task.id)

    def on_task_status_toggled(self, event: TaskStatusToggled) -> None:
        """Handle task status toggle from the task list widget."""
        if self.database:
            self.database.update_task_status(event.task_id, event.new_status)
            self._load_tasks(select_task_id=event.task_id)

    def on_task_deleted(self, event: TaskDeleted) -> None:
        """Handle task deletion from the task list widget."""
        if self.database:
            task_list_view = self.query_one(TaskListView)
            task_list = task_list_view.query_one("#task-list", SimpleTaskList)

            # Find the next task to select after deletion
            next_task_id: int | None = None
            try:
                idx = task_list._task_ids.index(event.task_id)
                if idx < len(task_list._task_ids) - 1:
                    next_task_id = task_list._task_ids[idx + 1]
                elif idx > 0:
                    next_task_id = task_list._task_ids[idx - 1]
            except ValueError:
                pass

            self.database.delete_task(event.task_id)
            self._load_tasks(select_task_id=next_task_id)

    def on_task_edited(self, event: TaskEdited) -> None:
        """Handle task title edit from the task list widget."""
        if self.database:
            task_list_view = self.query_one(TaskListView)
            task_list_view.hide_edit()
            self.database.update_task_title(event.task_id, event.new_title)
            self._load_tasks(select_task_id=event.task_id)

    def on_status_bar_update(self, event: StatusBarUpdate) -> None:
        """Handle status bar updates from widgets."""
        status_bar = self.query_one("#status-bar", Static)
        if event.text:
            status_bar.update(event.text)
            status_bar.remove_class("hidden")
        else:
            status_bar.update("")
            status_bar.add_class("hidden")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"


def main() -> None:
    """Run the application."""
    app = TaskNerdApp()
    app.run()


if __name__ == "__main__":
    main()
