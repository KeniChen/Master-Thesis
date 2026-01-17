"""Batch files management routes."""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from saed.core.batches import BatchRegistry, load_batch_file
from saed.core.batches.loader import get_batch_preview, validate_batch_file
from saed.core.config.settings import get_absolute_path, load_config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_batches_dir() -> Path:
    """Get the batches directory path."""
    config = load_config()
    return get_absolute_path(config.paths.batches)


def get_registry() -> BatchRegistry:
    """Get or create the batch registry."""
    batches_dir = get_batches_dir()
    batches_dir.mkdir(parents=True, exist_ok=True)
    return BatchRegistry.load(batches_dir)


@router.get("")
async def list_batches() -> dict[str, Any]:
    """List all available batch files."""
    registry = get_registry()

    # Registry is synced on API startup via lifespan handler
    batches = []
    for entry in registry.list_all():
        batches.append({
            "id": entry.id,
            "filename": entry.filename,
            "name": entry.name,
            "description": entry.description,
            "run_id": entry.run_id,
            "created_at": entry.created_at if entry.created_at else None,
            "config": {
                "ontology_id": entry.config.ontology_id,
                "mode": entry.config.mode,
                "prompt_type": entry.config.prompt_type,
                "max_depth": entry.config.max_depth,
                "k": entry.config.k,
                "provider": entry.config.provider,
                "model": entry.config.model,
            },
            "stats": {
                "total_tables": entry.total_tables,
                "total_columns": entry.total_columns,
                "completed_columns": entry.completed_columns,
            },
        })

    return {"batches": batches}


@router.post("/upload")
async def upload_batch(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """Upload a new batch file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")

    batches_dir = get_batches_dir()
    batches_dir.mkdir(parents=True, exist_ok=True)

    file_path = batches_dir / file.filename
    content = await file.read()

    # Write file
    with open(file_path, "wb") as f:
        f.write(content)

    # Validate by loading
    try:
        import json
        data = json.loads(content.decode("utf-8"))

        # Validate structure
        errors = validate_batch_file(data)
        if errors:
            file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Invalid batch file: {', '.join(errors)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}") from None

    # Register
    registry = get_registry()
    entry = registry.register(file.filename)

    logger.info(f"Uploaded batch {entry.id} ({file.filename}) with {entry.total_columns} columns")

    return {
        "id": entry.id,
        "filename": entry.filename,
        "name": entry.name,
        "run_id": entry.run_id,
        "config": {
            "ontology_id": entry.config.ontology_id,
            "mode": entry.config.mode,
            "prompt_type": entry.config.prompt_type,
            "max_depth": entry.config.max_depth,
            "k": entry.config.k,
            "provider": entry.config.provider,
            "model": entry.config.model,
        },
        "stats": {
            "total_tables": entry.total_tables,
            "total_columns": entry.total_columns,
            "completed_columns": entry.completed_columns,
        },
    }


@router.get("/{batch_id}")
async def get_batch(batch_id: str) -> dict[str, Any]:
    """Get batch file details."""
    registry = get_registry()

    # Try by ID first, then by filename
    entry = registry.get(batch_id)
    if entry is None:
        entry = registry.get_by_filename(batch_id)

    if entry is None:
        raise HTTPException(status_code=404, detail="Batch file not found")

    return {
        "id": entry.id,
        "filename": entry.filename,
        "name": entry.name,
        "description": entry.description,
        "run_id": entry.run_id,
        "created_at": entry.created_at if entry.created_at else None,
        "config": {
            "ontology_id": entry.config.ontology_id,
            "mode": entry.config.mode,
            "prompt_type": entry.config.prompt_type,
            "max_depth": entry.config.max_depth,
            "k": entry.config.k,
            "provider": entry.config.provider,
            "model": entry.config.model,
        },
        "stats": {
            "total_tables": entry.total_tables,
            "total_columns": entry.total_columns,
            "completed_columns": entry.completed_columns,
        },
    }


@router.get("/{batch_id}/preview")
async def preview_batch(
    batch_id: str,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> dict[str, Any]:
    """Preview batch file content."""
    registry = get_registry()
    batches_dir = get_batches_dir()

    # Resolve ID
    entry = registry.get(batch_id)
    if entry is None:
        entry = registry.get_by_filename(batch_id)

    if entry is None:
        # Try direct filename
        file_path = batches_dir / batch_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Batch file not found")
    else:
        file_path = batches_dir / entry.filename

    try:
        data = load_batch_file(file_path)
        preview = get_batch_preview(data, limit=limit)
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading batch: {e}") from None


@router.delete("/{batch_id}")
async def delete_batch(batch_id: str) -> dict[str, str]:
    """Delete a batch file."""
    registry = get_registry()
    batches_dir = get_batches_dir()

    # Resolve ID
    entry = registry.get(batch_id)
    if entry is None:
        entry = registry.get_by_filename(batch_id)

    if entry is None:
        # Try direct filename
        file_path = batches_dir / batch_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Batch file not found")
        file_path.unlink()
        return {"message": "Batch file deleted successfully"}

    # Delete file
    file_path = batches_dir / entry.filename
    if file_path.exists():
        file_path.unlink()

    # Remove from registry
    registry.unregister(entry.id)

    logger.info(f"Deleted batch {entry.id}")
    return {"message": "Batch file deleted successfully"}
