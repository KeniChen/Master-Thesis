"""Labels file loading and parsing utilities."""

from pathlib import Path

import pandas as pd


def load_labels_file(file_path: Path) -> pd.DataFrame:
    """Load a labels CSV file.

    Args:
        file_path: Path to the labels CSV file

    Returns:
        DataFrame with labels data

    Expected columns:
        - table_id: Table filename (e.g., "1.csv")
        - column_id: Column index (0-based)
        - column_name: Column name
        - class1_level1_name: First class level 1 (or "-" if none)
        - class1_level2_name: First class level 2 (or "-" if none)
        - class2_level1_name: Second class level 1 (or "-" if none)
        - class2_level2_name: Second class level 2 (or "-" if none)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Labels file not found: {file_path}")

    return pd.read_csv(file_path)


def parse_labels_to_paths(row: pd.Series) -> list[list[str]]:
    """Parse a labels row into ground truth paths.

    Args:
        row: A row from the labels DataFrame

    Returns:
        List of paths, where each path is a list of class names.
        E.g., [["TemporalEntity", "Interval"], ["Measurement", "PowerUnit"]]
    """
    paths = []

    # Parse first class path
    c1_l1 = row.get("class1_level1_name", "-")
    c1_l2 = row.get("class1_level2_name", "-")

    if pd.notna(c1_l1) and str(c1_l1) != "-":
        path = [str(c1_l1)]
        if pd.notna(c1_l2) and str(c1_l2) != "-":
            path.append(str(c1_l2))
        paths.append(path)

    # Parse second class path
    c2_l1 = row.get("class2_level1_name", "-")
    c2_l2 = row.get("class2_level2_name", "-")

    if pd.notna(c2_l1) and str(c2_l1) != "-":
        path = [str(c2_l1)]
        if pd.notna(c2_l2) and str(c2_l2) != "-":
            path.append(str(c2_l2))
        paths.append(path)

    return paths


def get_labels_for_column(
    df_labels: pd.DataFrame,
    table_id: str,
    column_id: int | None = None,
    column_name: str | None = None,
) -> list[list[str]] | None:
    """Get ground truth paths for a specific column.

    Args:
        df_labels: Labels DataFrame
        table_id: Table ID (filename)
        column_id: Column index (0-based)
        column_name: Column name (used if column_id not found)

    Returns:
        List of ground truth paths or None if not found
    """
    # Try matching by table_id and column_id first
    if column_id is not None:
        mask = (df_labels["table_id"] == table_id) & (df_labels["column_id"] == column_id)
        matches = df_labels[mask]
        if not matches.empty:
            return parse_labels_to_paths(matches.iloc[0])

    # Try matching by table_id and column_name
    if column_name is not None:
        mask = (df_labels["table_id"] == table_id) & (df_labels["column_name"] == column_name)
        matches = df_labels[mask]
        if not matches.empty:
            return parse_labels_to_paths(matches.iloc[0])

    return None


def paths_to_string(paths: list[list[str]], path_sep: str = "|", level_sep: str = "/") -> str:
    """Convert paths to string representation.

    Args:
        paths: List of paths
        path_sep: Separator between paths (default: "|")
        level_sep: Separator between levels (default: "/")

    Returns:
        String representation, e.g., "TemporalEntity/Interval|Measurement/PowerUnit"
    """
    return path_sep.join(level_sep.join(path) for path in paths)


def string_to_paths(s: str, path_sep: str = "|", level_sep: str = "/") -> list[list[str]]:
    """Parse string representation back to paths.

    Args:
        s: String representation
        path_sep: Separator between paths (default: "|")
        level_sep: Separator between levels (default: "/")

    Returns:
        List of paths
    """
    if not s or s == "-":
        return []
    return [path.split(level_sep) for path in s.split(path_sep)]
