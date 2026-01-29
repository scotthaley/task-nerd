"""Data models for Task Nerd."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task in the database."""

    id: int
    title: str
    description: str
    status: TaskStatus
    priority: int
    category: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Task":
        """Create a Task from a SQLite row dictionary."""
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=row["priority"],
            category=row["category"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
