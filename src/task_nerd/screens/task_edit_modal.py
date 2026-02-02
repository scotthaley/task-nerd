"""Task edit modal dialog."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea

from task_nerd.models import Task


class SubmitOnEnterTextArea(TextArea):
    """TextArea that posts a Submitted message on Enter, uses Shift+Enter for newlines."""

    class Submitted(TextArea.Changed):
        """Posted when Enter is pressed without Shift."""

        pass

    def _on_key(self, event) -> None:
        """Handle key events - Enter submits, Ctrl+Enter inserts newline."""
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self))
        elif event.key == "ctrl+enter":
            # Insert newline with ctrl+enter
            event.prevent_default()
            event.stop()
            self.insert("\n")
        else:
            super()._on_key(event)


class TaskEditModal(ModalScreen[tuple[str, str] | None]):
    """Modal dialog for editing a task's title and description."""

    CSS = """
    TaskEditModal {
        align: center middle;
        background: $background 60%;
    }

    TaskEditModal > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: solid $primary-muted;
        padding: 1 2;
    }

    TaskEditModal #modal-title {
        text-style: bold;
        margin-bottom: 1;
    }

    TaskEditModal .field-label {
        color: $text-muted;
        margin-bottom: 0;
    }

    TaskEditModal #title-input {
        border: none;
        background: transparent;
        padding: 0;
        height: 1;
        margin-bottom: 1;
    }

    TaskEditModal #title-input:focus {
        border: none;
    }

    TaskEditModal #description-area {
        height: 8;
        border: none;
        background: transparent;
        padding: 0;
    }

    TaskEditModal #description-area:focus {
        border: none;
    }

    TaskEditModal #description-area .text-area--cursor-line {
        background: transparent;
    }

    TaskEditModal #description-area .text-area--cursor-gutter {
        background: transparent;
    }

    TaskEditModal #button-row {
        margin-top: 1;
        height: auto;
    }

    TaskEditModal Button {
        min-width: 10;
        border: none;
        background: transparent;
        color: $text-muted;
        padding: 0 1;
        height: 1;
    }

    TaskEditModal Button:hover {
        background: $surface-lighten-1;
        color: $text;
    }

    TaskEditModal Button:focus {
        background: $surface-lighten-1;
        color: $text;
        text-style: bold;
    }

    TaskEditModal #save-btn {
        color: $success;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, task: Task) -> None:
        """Initialize the modal with a task to edit."""
        super().__init__()
        self._task = task

    def compose(self) -> ComposeResult:
        """Create dialog widgets."""
        with Vertical():
            yield Label("Edit Task", id="modal-title")
            yield Label("Title:", classes="field-label")
            yield Input(value=self._task.title, id="title-input")
            yield Label("Description:", classes="field-label")
            yield SubmitOnEnterTextArea(self._task.description or "", id="description-area")
            with Horizontal(id="button-row"):
                yield Button("[Enter] Save", id="save-btn")
                yield Button("[Esc] Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the title input when the modal opens."""
        self.query_one("#title-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in title input - save the task."""
        if event.input.id == "title-input":
            self._save()

    def on_submit_on_enter_text_area_submitted(
        self, event: SubmitOnEnterTextArea.Submitted
    ) -> None:
        """Handle Enter key in description area - save the task."""
        self._save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Handle Escape key - cancel editing."""
        self.dismiss(None)

    def _save(self) -> None:
        """Save the edited task."""
        title = self.query_one("#title-input", Input).value.strip()
        if not title:
            return  # Don't save empty title
        description = self.query_one("#description-area", TextArea).text
        self.dismiss((title, description))
