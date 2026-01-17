"""Table management routes."""

import logging
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from saed.api.schemas import TableInfo, TableListResponse, TablePreview
from saed.core.config.settings import get_absolute_path, load_config
from saed.core.table import TableRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tables_dir() -> Path:
    """Get the tables directory path."""
    config = load_config()
    return get_absolute_path(config.paths.tables)


def get_registry() -> TableRegistry:
    """Get or create the table registry."""
    tables_dir = get_tables_dir()
    return TableRegistry.load(tables_dir)


def resolve_table_id(table_id: str) -> tuple[str, Path, str]:
    """Resolve table ID to registry ID, file path, and category.

    Args:
        table_id: Table ID (registry ID or filename)

    Returns:
        Tuple of (registry_id, file_path, category)

    Raises:
        HTTPException: If table not found
    """
    registry = get_registry()
    tables_dir = get_tables_dir()

    # Try direct ID lookup
    entry = registry.get(table_id)
    if entry:
        if entry.category and entry.category != "default":
            file_path = tables_dir / entry.category / entry.filename
        else:
            file_path = tables_dir / entry.filename
        return entry.id, file_path, entry.category

    # Try by filename (search all categories)
    entry = registry.get_by_filename(table_id)
    if entry:
        if entry.category and entry.category != "default":
            file_path = tables_dir / entry.category / entry.filename
        else:
            file_path = tables_dir / entry.filename
        return entry.id, file_path, entry.category

    # Not in registry - check if file exists directly and register it
    # Check root directory
    file_path = tables_dir / table_id
    if file_path.exists() and file_path.suffix == ".csv":
        entry = registry.register(filename=table_id, category="default")
        return entry.id, file_path, "default"

    # Check subdirectories
    for subdir in tables_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("."):
            file_path = subdir / table_id
            if file_path.exists() and file_path.suffix == ".csv":
                entry = registry.register(filename=table_id, category=subdir.name)
                return entry.id, file_path, subdir.name

    raise HTTPException(status_code=404, detail="Table not found")


@router.get("", response_model=TableListResponse)
async def list_tables(
    category: Annotated[str | None, Query(description="Filter by category")] = None,
):
    """List all available tables."""
    registry = get_registry()

    # Registry is synced on API startup via lifespan handler
    # Build response from registry (fast - no CSV reads needed!)
    tables = []
    for entry in registry.list_all(category=category):
        tables.append(
            TableInfo(
                id=entry.id,
                name=entry.name,
                filename=entry.filename,
                columns=entry.columns,
                row_count=entry.row_count,
                column_count=entry.column_count,
                category=entry.category,
            )
        )

    return TableListResponse(tables=tables)


@router.post("")
async def upload_table(
    file: Annotated[UploadFile, File()],
    category: Annotated[str, Query(description="Category subdirectory")] = "default",
):
    """Upload a new CSV table."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    tables_dir = get_tables_dir()

    # Determine target directory
    target_dir = tables_dir / category if category and category != "default" else tables_dir

    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / file.filename
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    # Validate CSV
    try:
        pd.read_csv(file_path)
    except Exception as e:
        file_path.unlink()  # Remove invalid file
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {e}") from None

    # Register in registry
    registry = get_registry()
    entry = registry.register(
        filename=file.filename,
        category=category,
    )

    logger.info(f"Uploaded table {entry.id} ({file.filename}) to {category}")

    return {
        "id": entry.id,
        "name": entry.name,
        "filename": entry.filename,
        "columns": entry.columns,
        "row_count": entry.row_count,
        "category": entry.category,
    }


@router.get("/{table_id}", response_model=TablePreview)
async def get_table(table_id: str, limit: int = 10):
    """Get table details and preview."""
    registry_id, file_path, category = resolve_table_id(table_id)
    registry = get_registry()
    entry = registry.get(registry_id)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        df = pd.read_csv(file_path)
        preview_df = df.head(limit)

        return TablePreview(
            id=entry.id if entry else table_id,
            name=entry.name if entry else file_path.stem,
            columns=df.columns.tolist(),
            rows=preview_df.to_dict(orient="records"),
            total_rows=len(df),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading table: {e}") from None


@router.get("/{table_id}/preview")
async def preview_table(table_id: str, rows: int = 5):
    """Get table preview with specified number of rows."""
    return await get_table(table_id, limit=rows)


@router.put("/{table_id}")
async def update_table(table_id: str, data: dict):
    """Update table data."""
    registry_id, file_path, category = resolve_table_id(table_id)
    registry = get_registry()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        if "rows" not in data:
            raise HTTPException(status_code=400, detail="Missing 'rows' in request body")

        df = pd.DataFrame(data["rows"])
        df.to_csv(file_path, index=False)

        # Update registry entry (will detect hash change and update metadata)
        registry.update(registry_id)

        return {"message": "Table updated successfully", "row_count": len(df)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating table: {e}") from None


@router.delete("/{table_id}")
async def delete_table(table_id: str):
    """Delete a table."""
    registry_id, file_path, category = resolve_table_id(table_id)
    registry = get_registry()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Table not found")

    # Delete file
    file_path.unlink()

    # Remove from registry
    registry.unregister(registry_id)

    logger.info(f"Deleted table {registry_id}")
    return {"message": "Table deleted successfully"}


@router.post("/sync")
async def sync_tables():
    """Sync registry with directory (manual trigger)."""
    registry = get_registry()
    result = registry.sync_with_directory()

    return {
        "message": "Sync completed",
        "added": len(result["added"]),
        "removed": len(result["removed"]),
        "updated": len(result["updated"]),
        "details": result,
    }
