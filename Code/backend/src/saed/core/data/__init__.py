"""Backward-compatible exports for data utilities (deprecated)."""

from saed.core.table import (
    TableEntry,
    TableRegistry,
    dataframe_to_markdown,
    load_labels,
    load_table,
    load_table_list,
    load_tables,
)

__all__ = [
    "TableEntry",
    "TableRegistry",
    "dataframe_to_markdown",
    "load_labels",
    "load_table",
    "load_table_list",
    "load_tables",
]
