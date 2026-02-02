"""CLI commands for Task Nerd."""

import argparse
import json
import sys
from pathlib import Path

from task_nerd.database import Database
from task_nerd.models import Task, TaskStatus


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="task-nerd",
        description="Task Nerd - A TUI task manager",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ls command
    ls_parser = subparsers.add_parser("ls", help="List all tasks")
    ls_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output as JSON"
    )

    # edit command
    edit_parser = subparsers.add_parser("edit", help="Edit a task")
    edit_parser.add_argument(
        "--id", type=int, required=True, dest="task_id", help="Task ID to edit"
    )
    edit_parser.add_argument("--name", type=str, help="New title for the task")
    edit_parser.add_argument("--description", type=str, help="New description")
    edit_parser.add_argument("--category", type=str, help="New category")

    # mark command
    mark_parser = subparsers.add_parser("mark", help="Mark a task complete/incomplete")
    mark_parser.add_argument(
        "--id", type=int, required=True, dest="task_id", help="Task ID to mark"
    )
    mark_group = mark_parser.add_mutually_exclusive_group(required=True)
    mark_group.add_argument(
        "--complete", action="store_true", help="Mark task as completed"
    )
    mark_group.add_argument(
        "--incomplete", action="store_true", help="Mark task as pending"
    )

    return parser


def get_database() -> Database | None:
    """Get database connection if tasks.db exists."""
    db_path = Path.cwd() / "tasks.db"
    if not db_path.exists():
        print(
            "Error: No tasks.db found in current directory.\n"
            "Run 'task-nerd' to create a database first.",
            file=sys.stderr,
        )
        return None
    return Database(db_path)


def get_task_by_id(db: Database, task_id: int) -> Task | None:
    """Find a task by ID."""
    tasks = db.get_all_tasks()
    for task in tasks:
        if task.id == task_id:
            return task
    return None


def cmd_ls(args: argparse.Namespace) -> int:
    """List all tasks."""
    db = get_database()
    if db is None:
        return 1

    tasks = db.get_all_tasks()

    if args.json_output:
        output = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status.value,
                "category": t.category,
            }
            for t in tasks
        ]
        print(json.dumps(output, indent=2))
    else:
        # Table output
        print(f"{'ID':<4} {'STATUS':<10} {'CATEGORY':<12} TITLE")
        for task in tasks:
            status = task.status.value
            category = task.category if task.category else "-"
            # Truncate category and title if too long
            if len(category) > 10:
                category = category[:9] + "…"
            print(f"{task.id:<4} {status:<10} {category:<12} {task.title}")

    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    """Edit a task's title, description, or category."""
    db = get_database()
    if db is None:
        return 1

    # Check that at least one field is provided
    if args.name is None and args.description is None and args.category is None:
        print(
            "Error: At least one of --name, --description, or --category is required.",
            file=sys.stderr,
        )
        return 1

    task = get_task_by_id(db, args.task_id)
    if task is None:
        print(f"Error: Task with ID {args.task_id} not found.", file=sys.stderr)
        return 1

    # Build update values, keeping existing values for unspecified fields
    new_title = args.name if args.name is not None else task.title
    new_description = args.description if args.description is not None else task.description
    new_category = args.category if args.category is not None else task.category

    db.update_task(args.task_id, new_title, new_description, new_category)
    print(f"Updated task {args.task_id}.")
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    """Mark a task as complete or incomplete."""
    db = get_database()
    if db is None:
        return 1

    task = get_task_by_id(db, args.task_id)
    if task is None:
        print(f"Error: Task with ID {args.task_id} not found.", file=sys.stderr)
        return 1

    if args.complete:
        new_status = TaskStatus.COMPLETED
        status_word = "completed"
    else:
        new_status = TaskStatus.PENDING
        status_word = "pending"

    db.update_task_status(args.task_id, new_status)
    print(f"Marked task {args.task_id} as {status_word}.")
    return 0


def run_cli(argv: list[str] | None = None) -> int | None:
    """Parse arguments and dispatch to command handlers.

    Returns:
        Exit code (0 for success, non-zero for error) if a command was handled,
        None if no command was specified (should launch TUI).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return None

    if args.command == "ls":
        return cmd_ls(args)
    elif args.command == "edit":
        return cmd_edit(args)
    elif args.command == "mark":
        return cmd_mark(args)

    return None
