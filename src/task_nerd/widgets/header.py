"""Custom ASCII art header widget."""

from textual.widgets import Static


class AsciiArtHeader(Static):
    """A header widget displaying 'Task Nerd' in ASCII art."""

    DEFAULT_CSS = """
    AsciiArtHeader {
        height: 7;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $primary;
    }
    """

    ASCII_ART = """\
 _____         _      _   _              _
|_   _|_ _ ___| | __ | \\ | | ___ _ __ __| |
  | |/ _` / __| |/ / |  \\| |/ _ \\ '__/ _` |
  | | (_| \\__ \\   <  | |\\  |  __/ | | (_| |
  |_|\\__,_|___/_|\\_\\ |_| \\_|\\___|_|  \\__,_|
──────────────────────────────────────────"""

    def __init__(self) -> None:
        """Initialize the ASCII art header."""
        super().__init__(self.ASCII_ART)
