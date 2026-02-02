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

## CLI Commands

Task Nerd provides CLI commands to interact with tasks without launching the TUI:

### List Tasks

```bash
task-nerd ls          # Table format
task-nerd ls --json   # JSON format
```

Example output:
```
ID   STATUS     CATEGORY     TITLE
1    pending    -            Fix login bug
2    completed  work         Write documentation
3    pending    personal     Buy groceries
```

### Edit Tasks

```bash
task-nerd edit --id 1 --name "New title"
task-nerd edit --id 1 --description "New description"
task-nerd edit --id 1 --category "work"
task-nerd edit --id 1 --name "New title" --category "urgent"
```

At least one of `--name`, `--description`, or `--category` is required. Unspecified fields remain unchanged.

### Mark Tasks Complete/Incomplete

```bash
task-nerd mark --id 1 --complete    # Mark as completed
task-nerd mark --id 1 --incomplete  # Mark as pending
```

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

Task Nerd supports an optional configuration file at `~/.config/task-nerd/task-nerd.toml` for customization.

### Completed Date Format

Completed tasks show their completion date on the right side. You can customize the date format using Python's [strftime](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior) syntax:

```toml
completed_date_format = "%Y-%m-%d"  # ISO format: 2024-01-15
```

The default format is `%m/%d/%y` (e.g., `01/15/24`).

### Description Preview

The first 40 characters of a task's description can be shown underneath the task title. Configure with:

```toml
show_description_preview = "incomplete"  # default: only show for incomplete tasks
show_description_preview = "all"         # show for all tasks including completed
show_description_preview = "off"         # disable description preview
```

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

## Claude Code Integration

If you use [Claude Code](https://claude.ai/code), you can add the following to your project's `CLAUDE.md` file to teach Claude how to interact with your task-nerd database:

````markdown
## Task Management

This project uses [task-nerd](https://github.com/yourusername/task-nerd) for task management. Tasks are stored in `tasks.db` in the project root. When tasks are mentioned, they refer to this database.

### CLI Commands

```bash
# List all tasks
task-nerd ls

# List tasks as JSON (useful for parsing)
task-nerd ls --json

# Edit a task
task-nerd edit --id <id> --name "New title"
task-nerd edit --id <id> --description "New description"
task-nerd edit --id <id> --category "category-name"

# Mark a task complete or incomplete
task-nerd mark --id <id> --complete
task-nerd mark --id <id> --incomplete
```

### Task Structure

Tasks have the following fields:
- `id`: Unique integer identifier
- `title`: The task name/title
- `description`: Optional longer description
- `status`: Either "pending" or "completed"
- `category`: Optional category for grouping
````

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
