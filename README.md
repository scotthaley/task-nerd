# Task Nerd

A fast, keyboard-driven task management TUI (Terminal User Interface) built with Python and [Textual](https://textual.textualize.io/).

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)

## Features

- **Vim-style navigation** - Use `j`/`k` to move between tasks
- **Quick task entry** - Press `a` to add a task inline
- **Inline editing** - Edit tasks with `i`, `I`, or `s` (vim-style)
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
| `a` | Add a new task after the selected task |
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
