"""Main application module."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.containers import Vertical
from textual.theme import Theme
from textual.widgets import Footer, Header, Input, Static

from task_nerd.config import load_config
from task_nerd.database import Database
from task_nerd.models import TaskStatus
from task_nerd.screens import CreateDatabaseDialog
from task_nerd.utils import parse_task_title
from task_nerd.widgets import TaskListView
from task_nerd.widgets.task_list import (
    EscapePressedInList,
    SearchCancelled,
    SearchInputRow,
    SearchSubmitted,
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
    search_mode: reactive[bool] = reactive(False)
    search_term: reactive[str] = reactive("")

    BINDINGS = [
        ("a", "add_task", "Add task"),
        ("/", "start_search", "Search"),
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
        self._config = load_config()

    def _apply_theme(self) -> None:
        """Apply the configured theme."""
        if self._config.theme == "custom" and self._config.custom_theme:
            custom = self._config.custom_theme
            if custom.is_valid():
                # Build theme kwargs with only non-None values
                theme_kwargs: dict = {
                    "primary": custom.primary,
                    "dark": custom.dark,
                }
                if custom.secondary:
                    theme_kwargs["secondary"] = custom.secondary
                if custom.accent:
                    theme_kwargs["accent"] = custom.accent
                if custom.foreground:
                    theme_kwargs["foreground"] = custom.foreground
                if custom.background:
                    theme_kwargs["background"] = custom.background
                if custom.surface:
                    theme_kwargs["surface"] = custom.surface
                if custom.panel:
                    theme_kwargs["panel"] = custom.panel
                if custom.boost:
                    theme_kwargs["boost"] = custom.boost
                if custom.warning:
                    theme_kwargs["warning"] = custom.warning
                if custom.error:
                    theme_kwargs["error"] = custom.error
                if custom.success:
                    theme_kwargs["success"] = custom.success
                if custom.variables:
                    theme_kwargs["variables"] = custom.variables

                custom_theme = Theme(name=custom.name, **theme_kwargs)
                self.register_theme(custom_theme)
                self.theme = custom.name
                return

        # Fall back to built-in theme
        self.theme = self._config.theme

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

    #search-container {
        height: auto;
        width: 100%;
    }

    #search-container.hidden {
        display: none;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield TaskListView()
        yield Static("", id="status-bar", classes="hidden")
        yield Vertical(id="search-container", classes="hidden")
        yield Footer()

    def on_mount(self) -> None:
        """Handle application mount - check for database."""
        self._apply_theme()

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

    def _load_tasks(
        self, select_task_id: int | None = None, focus_list: bool = True
    ) -> None:
        """Load tasks from database into the task list view.

        Args:
            select_task_id: If provided, select this task after loading.
            focus_list: If True, focus the task list after loading.
        """
        if self.database:
            tasks = self.database.get_all_tasks()
            if self.hide_completed:
                tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
            if self.search_term:
                tasks = self._filter_tasks_by_search(tasks, self.search_term)
            task_list_view = self.query_one(TaskListView)
            is_filtered = bool(self.search_term) or self.hide_completed
            task_list_view.load_tasks(
                tasks,
                select_task_id=select_task_id,
                is_filtered=is_filtered,
                focus_list=focus_list,
            )

    def _filter_tasks_by_search(self, tasks: list, search_term: str) -> list:
        """Filter tasks by search term using substring and fuzzy matching.

        Args:
            tasks: List of tasks to filter.
            search_term: The search term to match against.

        Returns:
            Filtered list of tasks.
        """
        if not search_term:
            return tasks

        term_lower = search_term.lower()
        filtered = []
        for task in tasks:
            title_lower = task.title.lower()
            # First try substring match
            if term_lower in title_lower:
                filtered.append(task)
            # Then try fuzzy match
            elif self._fuzzy_match(term_lower, title_lower):
                filtered.append(task)
        return filtered

    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """Check if all chars in pattern appear in text in order.

        Args:
            pattern: The pattern to search for.
            text: The text to search in.

        Returns:
            True if pattern matches text fuzzily.
        """
        pattern_idx = 0
        for char in text:
            if pattern_idx < len(pattern) and char == pattern[pattern_idx]:
                pattern_idx += 1
        return pattern_idx == len(pattern)

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
        task_list_view = self.query_one(TaskListView)
        if task_list_view._editing or self.search_mode:
            return
        task_list_view.show_input()

    def action_start_search(self) -> None:
        """Start search mode."""
        task_list_view = self.query_one(TaskListView)
        if task_list_view._editing:
            return
        if self.search_mode:
            return

        self.search_mode = True
        # Hide status bar while searching
        status_bar = self.query_one("#status-bar", Static)
        status_bar.add_class("hidden")

        # Mount search input
        search_container = self.query_one("#search-container", Vertical)
        search_container.remove_class("hidden")
        search_row = SearchInputRow(initial_term=self.search_term)
        search_container.mount(search_row)

    def _exit_search_mode(self) -> None:
        """Exit search mode and clean up search input."""
        self.search_mode = False

        # Remove search input
        search_container = self.query_one("#search-container", Vertical)
        try:
            search_row = search_container.query_one(SearchInputRow)
            search_row.remove()
        except Exception:
            pass
        search_container.add_class("hidden")

        # Update status bar to show current filter
        self._update_search_status_bar()

    def _update_search_status_bar(self) -> None:
        """Update status bar to show current search term."""
        status_bar = self.query_one("#status-bar", Static)
        if self.search_term:
            status_bar.update(f"/{self.search_term}")
            status_bar.remove_class("hidden")
        else:
            status_bar.update("")
            status_bar.add_class("hidden")

    def action_cancel_input(self) -> None:
        """Hide the task input field, edit row, or clear search."""
        # If in search mode, exit search mode (keep filter)
        if self.search_mode:
            self._exit_search_mode()
            task_list_view = self.query_one(TaskListView)
            task_list_view.focus_list()
            return

        # If search term exists (and not in search mode), clear it
        if self.search_term:
            self.search_term = ""
            self._update_search_status_bar()
            task_list = self.query_one(TaskListView).query_one("#task-list", SimpleTaskList)
            self._load_tasks(select_task_id=task_list.selected_task_id)
            return

        # Otherwise, cancel input/edit
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
            # Show a new input row for continuous task creation (after refresh completes)
            self.call_after_refresh(task_list_view.show_input)

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
        # Don't update status bar if we're in search mode
        if self.search_mode:
            return
        status_bar = self.query_one("#status-bar", Static)
        if event.text:
            status_bar.update(event.text)
            status_bar.remove_class("hidden")
        else:
            # If we have a search term, show it instead
            if self.search_term:
                status_bar.update(f"/{self.search_term}")
                status_bar.remove_class("hidden")
            else:
                status_bar.update("")
                status_bar.add_class("hidden")

    def on_search_submitted(self, event: SearchSubmitted) -> None:
        """Handle search submission."""
        self.search_term = event.term
        self._exit_search_mode()
        task_list_view = self.query_one(TaskListView)
        task_list = task_list_view.query_one("#task-list", SimpleTaskList)
        self._load_tasks(select_task_id=task_list.selected_task_id)

    def on_search_cancelled(self, event: SearchCancelled) -> None:
        """Handle search cancellation (keep filter)."""
        # Get current search term from input before exiting
        try:
            search_container = self.query_one("#search-container", Vertical)
            search_row = search_container.query_one(SearchInputRow)
            search_input = search_row.query_one("#search-input", Input)
            self.search_term = search_input.value
        except Exception:
            pass

        self._exit_search_mode()
        task_list_view = self.query_one(TaskListView)
        task_list = task_list_view.query_one("#task-list", SimpleTaskList)
        self._load_tasks(select_task_id=task_list.selected_task_id)

    def on_escape_pressed_in_list(self, event: EscapePressedInList) -> None:
        """Handle escape pressed in task list - clear search if active."""
        if self.search_term:
            self.search_term = ""
            self._update_search_status_bar()
            task_list = self.query_one(TaskListView).query_one("#task-list", SimpleTaskList)
            self._load_tasks(select_task_id=task_list.selected_task_id)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for live filtering."""
        if event.input.id == "search-input" and self.search_mode:
            self.search_term = event.value
            task_list = self.query_one(TaskListView).query_one("#task-list", SimpleTaskList)
            # Don't focus the list - keep focus on search input
            self._load_tasks(select_task_id=task_list.selected_task_id, focus_list=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-input":
            self.post_message(SearchSubmitted(event.value))

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"


def main() -> None:
    """Run the application."""
    app = TaskNerdApp()
    app.run()


if __name__ == "__main__":
    main()
