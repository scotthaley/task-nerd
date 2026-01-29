# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Task Nerd is a terminal user interface (TUI) application built with Python and the Textual framework.

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in development mode (includes dev dependencies)
pip install -e ".[dev]"

# Run the application
task-nerd
# Or directly:
python -m task_nerd.app
```

## Architecture

- **Entry point**: `task-nerd` CLI command maps to `task_nerd.app:main()`
- **Main application**: `src/task_nerd/app.py` - Contains `TaskNerdApp` class extending `textual.app.App`
- **Framework**: Textual (>=0.85.0) for TUI components

The application uses Textual's composition pattern with `compose()` returning widgets (Header, Footer, Static) and action methods for key bindings.

## SQLite Storage

Task Nerd stores tasks in a SQLite database file `tasks.db` in the current working directory.

### Database Behavior

- **First run**: If `tasks.db` doesn't exist, the app prompts to create it
- **Subsequent runs**: The app opens the existing database directly
- **Location**: `tasks.db` is created in the directory where you run `task-nerd`

### Schema

The database contains two tables:
- `tasks`: Stores task data (id, title, description, status, priority, created_at, updated_at)
- `schema_version`: Tracks schema version for future migrations

### Inspecting the Database

```bash
# View schema
sqlite3 tasks.db ".schema"

# View all tasks
sqlite3 tasks.db "SELECT * FROM tasks"

# Check schema version
sqlite3 tasks.db "SELECT * FROM schema_version"
```
