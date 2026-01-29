"""Utility functions for Task Nerd."""


def parse_task_title(raw_title: str) -> tuple[str, str | None]:
    """Parse a task title, extracting category from #tag syntax.

    The category is taken from everything after the LAST '#' character.

    Args:
        raw_title: The raw input string, e.g., "implement password reset #auth"

    Returns:
        A tuple of (title, category). Category is None if no valid category found.

    Examples:
        >>> parse_task_title("buy milk")
        ("buy milk", None)
        >>> parse_task_title("implement password reset #auth")
        ("implement password reset", "auth")
        >>> parse_task_title("add ping #networking system")
        ("add ping", "networking system")
        >>> parse_task_title("task with #multiple #tags")
        ("task with #multiple", "tags")
    """
    if "#" not in raw_title:
        return raw_title.strip(), None

    # Find the last '#' and split there
    last_hash_index = raw_title.rfind("#")
    title_part = raw_title[:last_hash_index].strip()
    category_part = raw_title[last_hash_index + 1 :].strip()

    # If category is empty or title is empty, treat as uncategorized
    if not category_part or not title_part:
        return raw_title.strip(), None

    return title_part, category_part
