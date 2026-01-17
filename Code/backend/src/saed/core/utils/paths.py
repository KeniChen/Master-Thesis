"""Path utilities for the SAED project."""

from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to the project root (where backend/, frontend/, data/ are located).
    """
    current = Path(__file__).resolve()
    # Navigate up from backend/src/saed/utils/paths.py to project root
    # paths.py -> utils -> saed -> src -> backend -> project_root
    return current.parent.parent.parent.parent.parent.parent


def get_backend_root() -> Path:
    """Get the backend directory path."""
    return get_project_root() / "backend"


def get_data_dir() -> Path:
    """Get the data directory path."""
    return get_project_root() / "data"


def get_output_dir() -> Path:
    """Get the outputs directory path."""
    return get_project_root() / "outputs"


def get_config_dir() -> Path:
    """Get the config directory path."""
    return get_project_root() / "config"
