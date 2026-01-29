"""Dialog screens for Task Nerd."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class CreateDatabaseDialog(ModalScreen[bool]):
    """Modal dialog prompting user to create the database."""

    CSS = """
    CreateDatabaseDialog {
        align: center middle;
    }

    CreateDatabaseDialog > Vertical {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    CreateDatabaseDialog #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    CreateDatabaseDialog #message {
        margin-bottom: 1;
    }

    CreateDatabaseDialog #path {
        color: $text-muted;
        margin-bottom: 1;
    }

    CreateDatabaseDialog Center {
        margin-top: 1;
    }

    CreateDatabaseDialog Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("enter", "create", "Create Database"),
        ("escape", "exit_app", "Exit"),
    ]

    def __init__(self, db_path: Path) -> None:
        """Initialize dialog with database path."""
        super().__init__()
        self.db_path = db_path

    def compose(self) -> ComposeResult:
        """Create dialog widgets."""
        with Vertical():
            yield Static("Database Not Found", id="title")
            yield Label(
                "No tasks database was found. Would you like to create one?",
                id="message",
            )
            yield Static(f"Path: {self.db_path}", id="path")
            with Center():
                yield Button("Create Database", variant="primary", id="create")
                yield Button("Exit", variant="default", id="exit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_create(self) -> None:
        """Handle Enter key - create database."""
        self.dismiss(True)

    def action_exit_app(self) -> None:
        """Handle Escape key - exit application."""
        self.dismiss(False)
