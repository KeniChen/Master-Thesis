"""Batch file loader utilities."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_batch_file(file_path: Path) -> dict[str, Any]:
    """Load a batch JSON file.

    Args:
        file_path: Path to the batch JSON file

    Returns:
        Parsed batch data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Batch file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    logger.debug(f"Loaded batch file: {file_path}")
    return data


def validate_batch_file(data: dict[str, Any]) -> list[str]:
    """Validate batch file structure.

    Args:
        data: Parsed batch data

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required top-level fields
    if "run_id" not in data:
        errors.append("Missing required field: run_id")

    if "config" not in data:
        errors.append("Missing required field: config")

    if "tables" not in data:
        errors.append("Missing required field: tables")
    elif not isinstance(data["tables"], list):
        errors.append("Field 'tables' must be a list")

    # Check config fields
    config = data.get("config", {})
    required_config = ["ontology_id", "mode", "prompt_type"]
    for field in required_config:
        if field not in config:
            errors.append(f"Missing config field: {field}")

    return errors


def get_batch_preview(data: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    """Get a preview of batch content.

    Args:
        data: Parsed batch data
        limit: Maximum number of tables to include

    Returns:
        Preview data with limited tables
    """
    tables = data.get("tables", [])[:limit]

    preview_tables = []
    for table in tables:
        columns = table.get("columns", [])
        preview_columns = []
        for col in columns[:5]:  # Limit columns per table
            preview_columns.append({
                "column_name": col.get("column_name", ""),
                "status": col.get("status", ""),
                "final_paths": col.get("final_paths", []),
            })

        preview_tables.append({
            "table_id": table.get("table_id", ""),
            "table_name": table.get("table_name", ""),
            "columns": preview_columns,
            "total_columns": len(table.get("columns", [])),
        })

    return {
        "run_id": data.get("run_id", ""),
        "config": data.get("config", {}),
        "summary": data.get("summary", {}),
        "tables": preview_tables,
        "total_tables": len(data.get("tables", [])),
        "preview_tables": len(preview_tables),
    }
