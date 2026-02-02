"""Configuration file support for Task Nerd."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONFIG_FILE = Path.home() / ".config" / "task-nerd" / "task-nerd.toml"

DEFAULT_THEME = "catppuccin-mocha"
DEFAULT_COMPLETED_DATE_FORMAT = "%m/%d/%y"
DEFAULT_SHOW_DESCRIPTION_PREVIEW = "incomplete"  # "off", "all", or "incomplete"


@dataclass
class CustomThemeConfig:
    """Configuration for a custom theme."""

    name: str
    dark: bool = True
    primary: str = ""
    secondary: str | None = None
    accent: str | None = None
    foreground: str | None = None
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    boost: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    variables: dict[str, str] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if the custom theme has all required fields."""
        return bool(self.primary)


@dataclass
class Config:
    """Application configuration."""

    theme: str = DEFAULT_THEME
    custom_theme: CustomThemeConfig | None = None
    completed_date_format: str = DEFAULT_COMPLETED_DATE_FORMAT
    show_description_preview: str = DEFAULT_SHOW_DESCRIPTION_PREVIEW


def load_config() -> Config:
    """Load configuration from the config file.

    Returns the default configuration if:
    - The config file doesn't exist
    - The config file has invalid TOML syntax
    - Any other error occurs during loading

    Returns:
        Config object with loaded or default values.
    """
    if not CONFIG_FILE.exists():
        return Config()

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        # Invalid TOML or read error - use defaults
        return Config()

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse configuration from a dictionary.

    Args:
        data: Dictionary from parsed TOML file.

    Returns:
        Config object with parsed values.
    """
    config = Config()

    # Load theme name
    if "theme" in data and isinstance(data["theme"], str):
        config.theme = data["theme"]

    # Load completed date format
    if "completed_date_format" in data and isinstance(data["completed_date_format"], str):
        config.completed_date_format = data["completed_date_format"]

    # Load show_description_preview
    if "show_description_preview" in data and isinstance(data["show_description_preview"], str):
        value = data["show_description_preview"]
        if value in ("off", "all", "incomplete"):
            config.show_description_preview = value

    # Load custom theme if present
    if "custom_theme" in data and isinstance(data["custom_theme"], dict):
        custom_data = data["custom_theme"]
        config.custom_theme = CustomThemeConfig(
            name=custom_data.get("name", "custom"),
            dark=custom_data.get("dark", True),
            primary=custom_data.get("primary", ""),
            secondary=custom_data.get("secondary"),
            accent=custom_data.get("accent"),
            foreground=custom_data.get("foreground"),
            background=custom_data.get("background"),
            surface=custom_data.get("surface"),
            panel=custom_data.get("panel"),
            boost=custom_data.get("boost"),
            warning=custom_data.get("warning"),
            error=custom_data.get("error"),
            success=custom_data.get("success"),
            variables=custom_data.get("variables", {}),
        )

    return config
