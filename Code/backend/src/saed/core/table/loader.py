"""Data loading utilities."""

from pathlib import Path

import pandas as pd

from saed.core.config.settings import Config, get_absolute_path, load_config


def get_tables_dir(config: Config | None = None) -> Path:
    """Get the tables directory path.

    Args:
        config: Optional configuration. If not provided, loads from file.

    Returns:
        Path to the tables directory.
    """
    if config is None:
        config = load_config()
    return get_absolute_path(config.paths.tables)


def get_labels_dir(config: Config | None = None) -> Path:
    """Get the labels directory path.

    Args:
        config: Optional configuration. If not provided, loads from file.

    Returns:
        Path to the labels directory.
    """
    if config is None:
        config = load_config()
    return get_absolute_path(config.paths.labels)


def load_table_list(config: Config | None = None) -> pd.DataFrame:
    """Load the list of tables from CSV.

    Args:
        config: Optional configuration. If not provided, loads from file.

    Returns:
        DataFrame with table list information.
    """
    tables_path = get_tables_dir(config)
    table_list_path = tables_path / "table_list.csv"
    if table_list_path.exists():
        return pd.read_csv(table_list_path)
    # Return empty DataFrame with expected columns if file doesn't exist
    return pd.DataFrame(columns=["table_id", "table_name"])


def load_tables(config: Config | None = None) -> dict[str, pd.DataFrame]:
    """Load all tables into a dictionary.

    Args:
        config: Optional configuration. If not provided, loads from file.

    Returns:
        Dictionary mapping table_id to DataFrame.
    """
    tables_path = get_tables_dir(config)
    table_list = load_table_list(config)
    tables = {}
    for table_id in table_list["table_id"]:
        table_file = tables_path / table_id
        if table_file.exists():
            tables[table_id] = pd.read_csv(table_file)
    return tables


def load_labels(config: Config | None = None) -> pd.DataFrame:
    """Load ground truth labels.

    Args:
        config: Optional configuration. If not provided, loads from file.

    Returns:
        DataFrame with ground truth labels.
    """
    labels_path = get_labels_dir(config)
    ground_truth_path = labels_path / "ground_truth.csv"
    if ground_truth_path.exists():
        return pd.read_csv(ground_truth_path)
    # Return empty DataFrame with expected columns if file doesn't exist
    return pd.DataFrame(columns=[
        "table_id", "column_id", "column_name",
        "class1_level1_name", "class1_level2_name",
        "class2_level1_name", "class2_level2_name"
    ])


def load_table(table_id: str, config: Config | None = None) -> pd.DataFrame:
    """Load a single table by ID.

    Args:
        table_id: The ID of the table to load.
        config: Optional configuration. If not provided, loads from file.

    Returns:
        DataFrame with the table data.

    Raises:
        FileNotFoundError: If the table file doesn't exist.
    """
    tables_path = get_tables_dir(config)
    table_file = tables_path / table_id
    if not table_file.exists():
        raise FileNotFoundError(f"Table not found: {table_id}")
    return pd.read_csv(table_file)
