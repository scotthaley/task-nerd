"""Main application module."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from task_nerd.database import Database
from task_nerd.screens import CreateDatabaseDialog
from task_nerd.utils import parse_task_title
from task_nerd.widgets import TaskListView
from task_nerd.widgets.task_list import TaskCreated, TaskStatusToggled


class TaskNerdApp(App):
    """A Textual app for task-nerd."""

    BINDINGS = [
        ("a", "add_task", "Add task"),
        ("escape", "cancel_input", "Cancel"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self.db_path = Path.cwd() / "tasks.db"
        self.database: Database | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield TaskListView()
        yield Footer()

    def on_mount(self) -> None:
        """Handle application mount - check for database."""
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

    def _load_tasks(self) -> None:
        """Load tasks from database into the task list view."""
        if self.database:
            tasks = self.database.get_all_tasks()
            task_list_view = self.query_one(TaskListView)
            task_list_view.load_tasks(tasks)
            task_list_view.focus_list()

    def action_add_task(self) -> None:
        """Show the task input field."""
        self.query_one(TaskListView).show_input()

    def action_cancel_input(self) -> None:
        """Hide the task input field."""
        self.query_one(TaskListView).hide_input()

    def on_task_created(self, event: TaskCreated) -> None:
        """Handle task creation from the task list widget."""
        if self.database:
            title, category = parse_task_title(event.title)
            self.database.create_task(title, category)
            self._load_tasks()

    def on_task_status_toggled(self, event: TaskStatusToggled) -> None:
        """Handle task status toggle from the task list widget."""
        if self.database:
            task_list_view = self.query_one(TaskListView)
            task_list = task_list_view.query_one("#task-list")
            current_index = task_list.index
            self.database.update_task_status(event.task_id, event.new_status)
            self._load_tasks()

            def restore_selection() -> None:
                task_list.index = current_index
                task_list.focus()

            self.call_after_refresh(restore_selection)

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"


def main() -> None:
    """Run the application."""
    app = TaskNerdApp()
    app.run()


if __name__ == "__main__":
    main()
