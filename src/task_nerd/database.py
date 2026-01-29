"""Database management for Task Nerd."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from task_nerd.models import Task, TaskStatus

CURRENT_SCHEMA_VERSION = 2


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Path) -> None:
        """Initialize database with path."""
        self.db_path = db_path

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections with dict-like row access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        with self.connection() as conn:
            cursor = conn.cursor()

            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    category TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # Create schema version table for future migrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # Insert initial schema version if not present
            cursor.execute(
                "SELECT version FROM schema_version WHERE version = ?",
                (CURRENT_SCHEMA_VERSION,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (CURRENT_SCHEMA_VERSION,),
                )

            conn.commit()

    def get_schema_version(self) -> int | None:
        """Get the current schema version, or None if not initialized."""
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT MAX(version) as version FROM schema_version"
                )
                row = cursor.fetchone()
                return row["version"] if row else None
            except sqlite3.OperationalError:
                return None

    def verify_connection(self) -> bool:
        """Verify the database connection and schema are valid."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM tasks LIMIT 1")
                return True
        except sqlite3.Error:
            return False

    def migrate_schema(self) -> None:
        """Run any pending schema migrations."""
        current_version = self.get_schema_version()
        if current_version is None:
            return

        with self.connection() as conn:
            cursor = conn.cursor()

            # Migration v1 -> v2: Add category column
            if current_version < 2:
                cursor.execute(
                    "ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT NULL"
                )
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (2,)
                )
                conn.commit()

    def get_all_tasks(self) -> list["Task"]:
        """Fetch all tasks ordered by category then created_at.

        Uncategorized tasks appear first, then tasks grouped by category
        alphabetically, with each group sorted by created_at descending.
        """
        from task_nerd.models import Task

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, description, status, priority, category, created_at, updated_at
                FROM tasks
                ORDER BY
                    CASE WHEN category IS NULL THEN 0 ELSE 1 END,
                    category ASC,
                    created_at DESC
            """)
            return [Task.from_row(dict(row)) for row in cursor.fetchall()]

    def create_task(self, title: str, category: str | None = None) -> "Task":
        """Create a new task with given title and optional category."""
        from task_nerd.models import Task

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (title, category) VALUES (?, ?)",
                (title, category),
            )
            conn.commit()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,))
            return Task.from_row(dict(cursor.fetchone()))

    def update_task_status(self, task_id: int, status: "TaskStatus") -> None:
        """Update the status of a task."""
        from task_nerd.models import TaskStatus

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status.value, task_id)
            )
            conn.commit()

    def delete_task(self, task_id: int) -> None:
        """Delete a task by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
