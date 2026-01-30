# Task Nerd

A fast, keyboard-driven task management TUI (Terminal User Interface) built with Python and [Textual](https://textual.textualize.io/).

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)

## Features

- **Vim-style navigation** - Use `j`/`k` to move between tasks
- **Quick task entry** - Press `o` to add a task inline
- **Inline editing** - Edit tasks with `a`, `i`, `I`, or `s` (vim-style)
- **Categories** - Organize tasks with `#category` syntax (e.g., `fix login bug #auth`)
- **Fuzzy search** - Press `/` to filter tasks with substring and fuzzy matching
- **Hide completed** - Toggle completed task visibility with `F1`
- **Persistent storage** - Tasks stored in a local SQLite database
- **Dark/light mode** - Toggle with `D`

## Installation

### Install globally with pip

```bash
pip install .
```

Or install in development mode:

```bash
pip install -e .
```

### Install globally with pipx (recommended)

[pipx](https://pipx.pypa.io/) installs Python CLI tools in isolated environments:

```bash
pipx install .
```

After installation, the `task-nerd` command will be available globally.

## Usage

Run the app:

```bash
task-nerd
```

On first run, the app will prompt you to create a `tasks.db` database file in the current directory.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `o` | Add a new task after the selected task |
| `a` | Edit task (cursor at end) |
| `i` | Edit task (cursor at end) |
| `I` | Edit task (cursor at beginning) |
| `s` | Edit task (replace text) |
| `space` | Toggle task completion |
| `dd` | Delete task (press `d` twice) |
| `j` / `k` | Move down / up |
| `/` | Search/filter tasks |
| `F1` | Toggle hide completed tasks |
| `D` | Toggle dark/light mode |
| `Escape` | Cancel current action or clear search |
| `q` | Quit |

### Categories

Organize tasks into categories using `#` syntax when creating or editing:

```
fix authentication bug #backend
update user docs #docs
add dark mode toggle #frontend
```

Tasks with the same category are grouped together under a header.

### Search

Press `/` to open the search bar. The search supports:

- **Substring matching** - `log` matches "login", "dialog", etc.
- **Fuzzy matching** - `fxbg` matches "fix bug"

The filter is applied in real-time as you type. Press `Enter` to confirm or `Escape` to close the search bar (filter remains active). Press `Escape` again to clear the filter.

## Data Storage

Task Nerd stores tasks in a SQLite database file (`tasks.db`) in the directory where you run the command. Each project/directory can have its own task database.

### Inspecting the Database

```bash
# View all tasks
sqlite3 tasks.db "SELECT * FROM tasks"

# View schema
sqlite3 tasks.db ".schema"
```

## Configuration

Task Nerd supports an optional configuration file at `~/.config/task-nerd/task-nerd.toml` for customizing the theme.

### Changing the Built-in Theme

To use a different built-in Textual theme:

```toml
theme = "textual-dark"
```

Available built-in themes include: `catppuccin-mocha` (default), `textual-dark`, `textual-light`, `dracula`, `monokai`, `nord`, `gruvbox`, `solarized-light`, `tokyo-night`.

### Creating a Custom Theme

Set `theme = "custom"` and define your colors in the `[custom_theme]` section:

```toml
theme = "custom"

[custom_theme]
name = "my-theme"
dark = true
primary = "#88C0D0"       # Required
secondary = "#81A1C1"     # Optional - all below are optional
accent = "#B48EAD"
foreground = "#D8DEE9"
background = "#2E3440"
surface = "#3B4252"
panel = "#434C5E"
boost = "#4C566A"
warning = "#EBCB8B"
error = "#BF616A"
success = "#A3BE8C"

# Optional CSS variable overrides
[custom_theme.variables]
footer-key-foreground = "#88C0D0"
```

The `primary` color is required for custom themes. If it's missing, the app falls back to the default theme.

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/task-nerd.git
cd task-nerd

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run the app
task-nerd
```

## Requirements

- Python 3.10+
- Textual 0.85.0+

## License

MIT
