"""
config.py
---------
Application configuration: load from and save to a JSON file.
Persists window geometry and last-used folder across sessions.
"""

import json
import os
import sys
from pathlib import Path

APP_NAME = "PdfManager"
CONFIG_FILENAME = "config.json"
LEGACY_CONFIG_PATH = Path(__file__).parent / "pdf_manager_config.json"


def _get_user_config_dir() -> Path:
    """Return an OS-appropriate user config directory for the app."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
        return base / APP_NAME

    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    return base / APP_NAME


CONFIG_PATH = _get_user_config_dir() / CONFIG_FILENAME

_DEFAULTS: dict = {
    "window_geometry": "860x700",
    "last_folder": str(Path.home()),
    "session_input_files": [],
    "session_page_order": [],
    "session_last_output": None,
}


def load_config() -> dict:
    """
    Load configuration from JSON file.

    Returns the stored config merged over defaults so that any missing
    keys are always present.

    Returns:
        dict with configuration values.
    """
    config = dict(_DEFAULTS)
    source_path = CONFIG_PATH if CONFIG_PATH.exists() else LEGACY_CONFIG_PATH
    if source_path.exists():
        try:
            with open(source_path, "r") as f:
                stored = json.load(f)
            config.update(stored)
        except (json.JSONDecodeError, OSError):
            pass  # Fall back to defaults silently
    return config


def save_config(config: dict) -> None:
    """
    Persist configuration dictionary to JSON file.

    Args:
        config: dict of configuration values to save.
    """
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass  # Non-fatal; config just won't persist
