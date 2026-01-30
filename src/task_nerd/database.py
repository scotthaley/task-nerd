"""Database management for Task Nerd."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from task_nerd.models import Task, TaskStatus

CURRENT_SCHEMA_VERSION = 4


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
                    order_value INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    completed_at TEXT DEFAULT NULL
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
                current_version = 2

            # Migration v2 -> v3: Add order_value column
            if current_version < 3:
                cursor.execute(
                    "ALTER TABLE tasks ADD COLUMN order_value INTEGER DEFAULT 0"
                )
                # Populate existing tasks with order values per category
                # Each category starts fresh at 1000, 2000, 3000...
                cursor.execute("SELECT DISTINCT category FROM tasks")
                categories = [row["category"] for row in cursor.fetchall()]

                for cat in categories:
                    if cat is None:
                        cursor.execute(
                            "SELECT id FROM tasks WHERE category IS NULL ORDER BY created_at DESC"
                        )
                    else:
                        cursor.execute(
                            "SELECT id FROM tasks WHERE category = ? ORDER BY created_at DESC",
                            (cat,),
                        )
                    rows = cursor.fetchall()
                    for idx, row in enumerate(rows):
                        cursor.execute(
                            "UPDATE tasks SET order_value = ? WHERE id = ?",
                            ((idx + 1) * 1000, row["id"]),
                        )

                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (3,)
                )
                conn.commit()
                current_version = 3

            # Migration v3 -> v4: Add completed_at column
            if current_version < 4:
                cursor.execute(
                    "ALTER TABLE tasks ADD COLUMN completed_at TEXT DEFAULT NULL"
                )
                # Backfill existing completed tasks with updated_at
                cursor.execute(
                    "UPDATE tasks SET completed_at = updated_at WHERE status = 'completed'"
                )
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (4,)
                )
                conn.commit()

    def get_all_tasks(self) -> list["Task"]:
        """Fetch all tasks ordered by category, then by order_value within each category.

        Uncategorized tasks appear first, then tasks grouped by category
        alphabetically, with each group sorted by order_value ascending.
        """
        from task_nerd.models import Task

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, description, status, priority, category, order_value, created_at, updated_at, completed_at
                FROM tasks
                ORDER BY
                    CASE WHEN category IS NULL THEN 0 ELSE 1 END,
                    category ASC,
                    order_value ASC
            """)
            return [Task.from_row(dict(row)) for row in cursor.fetchall()]

    def create_task(self, title: str, category: str | None = None) -> "Task":
        """Create a new task with given title and optional category.

        Note: This method appends the task at the end. Use create_task_at_position
        for positioned insertion.
        """
        from task_nerd.models import Task

        with self.connection() as conn:
            cursor = conn.cursor()
            # Get the next order_value (max + 1000)
            cursor.execute("SELECT MAX(order_value) as max_order FROM tasks")
            row = cursor.fetchone()
            max_order = row["max_order"] if row["max_order"] is not None else 0
            order_value = max_order + 1000

            cursor.execute(
                "INSERT INTO tasks (title, category, order_value) VALUES (?, ?, ?)",
                (title, category, order_value),
            )
            conn.commit()
            cursor.execute(
                "SELECT id, title, description, status, priority, category, order_value, created_at, updated_at, completed_at FROM tasks WHERE id = ?",
                (cursor.lastrowid,),
            )
            return Task.from_row(dict(cursor.fetchone()))

    def update_task_status(self, task_id: int, status: "TaskStatus") -> None:
        """Update the status of a task."""
        from task_nerd.models import TaskStatus

        with self.connection() as conn:
            cursor = conn.cursor()
            if status == TaskStatus.COMPLETED:
                cursor.execute(
                    "UPDATE tasks SET status = ?, completed_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
                    (status.value, task_id)
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status = ?, completed_at = NULL, updated_at = datetime('now') WHERE id = ?",
                    (status.value, task_id)
                )
            conn.commit()

    def update_task_title(self, task_id: int, title: str) -> None:
        """Update the title of a task."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (title, task_id)
            )
            conn.commit()

    def delete_task(self, task_id: int) -> None:
        """Delete a task by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

    def create_task_at_position(
        self,
        title: str,
        category: str | None = None,
        after_task_id: int | None = None,
        before_task_id: int | None = None,
    ) -> "Task":
        """Create a new task positioned after or before the specified task.

        Args:
            title: The task title
            category: Optional category for the task
            after_task_id: ID of task to insert after, or None to append at end of category
            before_task_id: ID of task to insert before (takes precedence if both provided)

        Returns:
            The created Task
        """
        from task_nerd.models import Task

        with self.connection() as conn:
            cursor = conn.cursor()

            if before_task_id is not None:
                order_value = self._get_order_value_before(
                    cursor, before_task_id, category
                )
            else:
                order_value = self._get_next_order_value(cursor, after_task_id, category)

            cursor.execute(
                "INSERT INTO tasks (title, category, order_value) VALUES (?, ?, ?)",
                (title, category, order_value),
            )
            conn.commit()
            cursor.execute(
                "SELECT id, title, description, status, priority, category, order_value, created_at, updated_at, completed_at FROM tasks WHERE id = ?",
                (cursor.lastrowid,),
            )
            return Task.from_row(dict(cursor.fetchone()))

    def _get_next_order_value(
        self, cursor: "sqlite3.Cursor", after_task_id: int | None, category: str | None
    ) -> int:
        """Calculate the order_value for insertion after the given task within a category.

        Args:
            cursor: Database cursor to use
            after_task_id: ID of task to insert after, or None for end of category
            category: The category the new task will belong to

        Returns:
            The order_value to use for the new task
        """
        # Build category filter for queries
        if category is None:
            category_filter = "category IS NULL"
            category_params: tuple = ()
        else:
            category_filter = "category = ?"
            category_params = (category,)

        if after_task_id is None:
            # Append at end of category: use max + 1000
            cursor.execute(
                f"SELECT MAX(order_value) as max_order FROM tasks WHERE {category_filter}",
                category_params,
            )
            row = cursor.fetchone()
            max_order = row["max_order"] if row["max_order"] is not None else 0
            return max_order + 1000

        # Get the order_value of the task we're inserting after
        cursor.execute(
            "SELECT order_value, category FROM tasks WHERE id = ?", (after_task_id,)
        )
        row = cursor.fetchone()
        if row is None:
            # Task not found, append at end of category
            cursor.execute(
                f"SELECT MAX(order_value) as max_order FROM tasks WHERE {category_filter}",
                category_params,
            )
            row = cursor.fetchone()
            max_order = row["max_order"] if row["max_order"] is not None else 0
            return max_order + 1000

        after_order = row["order_value"]
        after_category = row["category"]

        # If inserting into a different category than the after_task, append at end of new category
        if after_category != category:
            cursor.execute(
                f"SELECT MAX(order_value) as max_order FROM tasks WHERE {category_filter}",
                category_params,
            )
            row = cursor.fetchone()
            max_order = row["max_order"] if row["max_order"] is not None else 0
            return max_order + 1000

        # Find the next task's order_value within the same category
        cursor.execute(
            f"SELECT order_value FROM tasks WHERE {category_filter} AND order_value > ? ORDER BY order_value ASC LIMIT 1",
            category_params + (after_order,),
        )
        next_row = cursor.fetchone()

        if next_row is None:
            # No task after in this category, use after_order + 1000
            return after_order + 1000

        next_order = next_row["order_value"]
        gap = next_order - after_order

        if gap > 1:
            # Use midpoint
            return (after_order + next_order) // 2

        # Gap exhausted - rebalance tasks in this category
        self._rebalance_order_values(cursor, category)

        # Re-fetch the after_order since it may have changed
        cursor.execute(
            "SELECT order_value FROM tasks WHERE id = ?", (after_task_id,)
        )
        row = cursor.fetchone()
        after_order = row["order_value"]

        # Find the next task's order_value again
        cursor.execute(
            f"SELECT order_value FROM tasks WHERE {category_filter} AND order_value > ? ORDER BY order_value ASC LIMIT 1",
            category_params + (after_order,),
        )
        next_row = cursor.fetchone()

        if next_row is None:
            return after_order + 1000

        return (after_order + next_row["order_value"]) // 2

    def _get_order_value_before(
        self, cursor: "sqlite3.Cursor", before_task_id: int, category: str | None
    ) -> int:
        """Calculate the order_value for insertion before the given task.

        Args:
            cursor: Database cursor to use
            before_task_id: ID of task to insert before
            category: The category the new task will belong to

        Returns:
            The order_value to use for the new task
        """
        # Build category filter for queries
        if category is None:
            category_filter = "category IS NULL"
            category_params: tuple = ()
        else:
            category_filter = "category = ?"
            category_params = (category,)

        # Get the order_value of the task we're inserting before
        cursor.execute(
            "SELECT order_value FROM tasks WHERE id = ?", (before_task_id,)
        )
        row = cursor.fetchone()
        if row is None:
            # Task not found, append at end of category
            cursor.execute(
                f"SELECT MAX(order_value) as max_order FROM tasks WHERE {category_filter}",
                category_params,
            )
            row = cursor.fetchone()
            max_order = row["max_order"] if row["max_order"] is not None else 0
            return max_order + 1000

        before_order = row["order_value"]

        # Find the previous task's order_value within the target category
        cursor.execute(
            f"SELECT order_value FROM tasks WHERE {category_filter} AND order_value < ? ORDER BY order_value DESC LIMIT 1",
            category_params + (before_order,),
        )
        prev_row = cursor.fetchone()

        if prev_row is None:
            # No task before in this category, use before_order - 1000
            # (or 500 if that would be <= 0)
            new_order = before_order - 1000
            if new_order <= 0:
                new_order = before_order // 2 if before_order > 1 else 1
            return new_order

        prev_order = prev_row["order_value"]
        gap = before_order - prev_order

        if gap > 1:
            # Use midpoint
            return (prev_order + before_order) // 2

        # Gap exhausted - rebalance tasks in this category
        self._rebalance_order_values(cursor, category)

        # Re-fetch the before_order since it may have changed
        cursor.execute(
            "SELECT order_value FROM tasks WHERE id = ?", (before_task_id,)
        )
        row = cursor.fetchone()
        before_order = row["order_value"]

        # Find the previous task's order_value again
        cursor.execute(
            f"SELECT order_value FROM tasks WHERE {category_filter} AND order_value < ? ORDER BY order_value DESC LIMIT 1",
            category_params + (before_order,),
        )
        prev_row = cursor.fetchone()

        if prev_row is None:
            return before_order - 1000 if before_order > 1000 else before_order // 2

        return (prev_row["order_value"] + before_order) // 2

    def _rebalance_order_values(
        self, cursor: "sqlite3.Cursor", category: str | None
    ) -> None:
        """Rebalance tasks within a category with fresh order values spaced by 1000."""
        if category is None:
            cursor.execute(
                "SELECT id FROM tasks WHERE category IS NULL ORDER BY order_value ASC"
            )
        else:
            cursor.execute(
                "SELECT id FROM tasks WHERE category = ? ORDER BY order_value ASC",
                (category,),
            )
        rows = cursor.fetchall()
        for idx, row in enumerate(rows):
            cursor.execute(
                "UPDATE tasks SET order_value = ? WHERE id = ?",
                ((idx + 1) * 1000, row["id"]),
            )
