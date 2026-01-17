"""Labels (Ground Truth) management routes."""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from saed.core.config.settings import get_absolute_path, load_config
from saed.core.labels import LabelsRegistry, load_labels_file

logger = logging.getLogger(__name__)

router = APIRouter()


def get_labels_dir() -> Path:
    """Get the labels directory path."""
    config = load_config()
    return get_absolute_path(config.paths.labels)


def get_registry() -> LabelsRegistry:
    """Get or create the labels registry."""
    labels_dir = get_labels_dir()
    return LabelsRegistry.load(labels_dir)


@router.get("")
async def list_labels() -> dict[str, Any]:
    """List all available ground truth label files."""
    registry = get_registry()

    # Registry is synced on API startup via lifespan handler
    labels = []
    for entry in registry.list_all():
        labels.append({
            "id": entry.id,
            "filename": entry.filename,
            "name": entry.name,
            "description": entry.description,
            "created_at": entry.created_at if entry.created_at else None,
            "stats": {
                "total_tables": entry.total_tables,
                "total_columns": entry.total_columns,
            },
        })

    return {"labels": labels}


@router.post("/upload")
async def upload_labels(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """Upload a new ground truth labels file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    labels_dir = get_labels_dir()
    labels_dir.mkdir(parents=True, exist_ok=True)

    file_path = labels_dir / file.filename
    content = await file.read()

    # Write file
    with open(file_path, "wb") as f:
        f.write(content)

    # Validate by loading
    try:
        df = load_labels_file(file_path)

        # Check required columns
        required_cols = ["table_id", "column_id", "column_name"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {e}") from None

    # Register
    registry = get_registry()
    entry = registry.register(
        file.filename,
        name=file.filename.replace(".csv", "").replace("_", " ").title(),
    )

    logger.info(f"Uploaded labels {entry.id} ({file.filename}) with {entry.total_columns} columns")

    return {
        "id": entry.id,
        "filename": entry.filename,
        "name": entry.name,
        "stats": {
            "total_tables": entry.total_tables,
            "total_columns": entry.total_columns,
        },
    }


@router.get("/{labels_id}")
async def get_labels(labels_id: str) -> dict[str, Any]:
    """Get labels file details."""
    registry = get_registry()

    # Try by ID first, then by filename
    entry = registry.get(labels_id)
    if entry is None:
        entry = registry.get_by_filename(labels_id)

    if entry is None:
        raise HTTPException(status_code=404, detail="Labels file not found")

    return {
        "id": entry.id,
        "filename": entry.filename,
        "name": entry.name,
        "description": entry.description,
        "created_at": entry.created_at if entry.created_at else None,
        "stats": {
            "total_tables": entry.total_tables,
            "total_columns": entry.total_columns,
        },
    }


@router.get("/{labels_id}/preview")
async def preview_labels(
    labels_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, Any]:
    """Preview labels file content."""
    registry = get_registry()
    labels_dir = get_labels_dir()

    # Resolve ID
    entry = registry.get(labels_id)
    if entry is None:
        entry = registry.get_by_filename(labels_id)

    if entry is None:
        # Try direct filename
        file_path = labels_dir / labels_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Labels file not found")
    else:
        file_path = labels_dir / entry.filename

    try:
        df = load_labels_file(file_path)

        # Convert to preview format
        columns = list(df.columns)
        rows = df.head(limit).to_dict(orient="records")

        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(df),
            "preview_rows": len(rows),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading labels: {e}") from None


@router.delete("/{labels_id}")
async def delete_labels(labels_id: str) -> dict[str, str]:
    """Delete a labels file."""
    registry = get_registry()
    labels_dir = get_labels_dir()

    # Resolve ID
    entry = registry.get(labels_id)
    if entry is None:
        entry = registry.get_by_filename(labels_id)

    if entry is None:
        # Try direct filename
        file_path = labels_dir / labels_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Labels file not found")
        file_path.unlink()
        return {"message": "Labels file deleted successfully"}

    # Delete file
    file_path = labels_dir / entry.filename
    if file_path.exists():
        file_path.unlink()

    # Remove from registry
    registry.unregister(entry.id)

    logger.info(f"Deleted labels {entry.id}")
    return {"message": "Labels file deleted successfully"}
