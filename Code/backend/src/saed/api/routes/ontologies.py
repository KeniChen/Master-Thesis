"""Ontology management routes."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from saed.api.schemas import (
    OntologyInfo,
    OntologyListResponse,
    OntologyNode,
    OntologyTree,
)
from saed.core.config.settings import get_absolute_path, load_config
from saed.core.ontology import (
    OntologyCache,
    OntologyDAG,
    OntologyRegistry,
    get_cache_dir,
    validate_ontology,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_ontologies_dir() -> Path:
    """Get the ontologies directory path."""
    config = load_config()
    return get_absolute_path(config.paths.ontologies)


def get_registry() -> OntologyRegistry:
    """Get or create the ontology registry."""
    ontologies_dir = get_ontologies_dir()
    return OntologyRegistry.load(ontologies_dir)


def get_cache() -> OntologyCache:
    """Get the ontology cache manager."""
    ontologies_dir = get_ontologies_dir()
    cache_dir = get_cache_dir(ontologies_dir)
    return OntologyCache(cache_dir)


def ensure_cached(ontology_id: str) -> None:
    """Ensure ontology is registered and cached.

    Args:
        ontology_id: Ontology ID (slug) or filename

    Raises:
        HTTPException: If ontology not found
    """
    registry = get_registry()
    cache = get_cache()
    ontologies_dir = get_ontologies_dir()

    # Try to find by ID first, then by filename
    entry = registry.get(ontology_id)
    if entry is None:
        entry = registry.get_by_filename(ontology_id)

    if entry is None:
        # Check if file exists but not registered
        for ext in (".rdf", ".owl"):
            file_path = ontologies_dir / f"{ontology_id}{ext}"
            if file_path.exists():
                # Register the ontology
                dag = OntologyDAG(file_path)
                dag.build_dag()
                entry = registry.register(
                    file_path.name,
                    class_count=len(dag.nodes),
                )
                # Build and save cache
                tree = cache.build_from_dag(dag, entry.file_hash)
                cache.save(entry.id, tree)
                # Update max_depth
                registry.update(entry.id, max_depth=tree.metadata.get("max_depth", 0))
                return

        # Try direct filename
        file_path = ontologies_dir / ontology_id
        if file_path.exists():
            dag = OntologyDAG(file_path)
            dag.build_dag()
            entry = registry.register(
                ontology_id,
                class_count=len(dag.nodes),
            )
            tree = cache.build_from_dag(dag, entry.file_hash)
            cache.save(entry.id, tree)
            registry.update(entry.id, max_depth=tree.metadata.get("max_depth", 0))
            return

        raise HTTPException(status_code=404, detail="Ontology not found")

    # Check if cache is valid
    if not cache.exists(entry.id) or not registry.is_cache_valid(entry.id):
        # Rebuild cache
        file_path = ontologies_dir / entry.filename
        dag = OntologyDAG(file_path)
        dag.build_dag()
        tree = cache.build_from_dag(dag, entry.file_hash)
        cache.save(entry.id, tree)
        registry.update(
            entry.id,
            class_count=len(dag.nodes),
            max_depth=tree.metadata.get("max_depth", 0),
        )


def resolve_ontology_id(ontology_id: str) -> str:
    """Resolve ontology ID (filename or slug) to registry ID.

    Args:
        ontology_id: Ontology ID or filename

    Returns:
        Registry ID (slug)

    Raises:
        HTTPException: If not found
    """
    registry = get_registry()

    # Try direct ID lookup
    entry = registry.get(ontology_id)
    if entry:
        return entry.id

    # Try by filename
    entry = registry.get_by_filename(ontology_id)
    if entry:
        return entry.id

    # Not found, ensure_cached will handle registration
    ensure_cached(ontology_id)
    entry = registry.get(ontology_id) or registry.get_by_filename(ontology_id)
    if entry:
        return entry.id

    raise HTTPException(status_code=404, detail="Ontology not found")


@router.get("", response_model=OntologyListResponse)
async def list_ontologies():
    """List all available ontologies."""
    registry = get_registry()

    # Registry is synced on API startup via lifespan handler
    # Ensure all ontologies are cached
    for entry in registry.list_all():
        try:
            ensure_cached(entry.id)
        except Exception as e:
            logger.warning(f"Failed to cache {entry.id}: {e}")

    # Build response from registry
    ontologies = []
    for entry in registry.list_all():
        ontologies.append(
            OntologyInfo(
                id=entry.id,
                class_count=entry.class_count,
                max_depth=entry.max_depth,
                filename=entry.filename,
            )
        )

    return OntologyListResponse(ontologies=ontologies)


@router.post("")
async def upload_ontology(file: Annotated[UploadFile, File()]):
    """Upload a new ontology file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not (file.filename.endswith(".rdf") or file.filename.endswith(".owl")):
        raise HTTPException(status_code=400, detail="Only RDF/OWL files are allowed")

    ontologies_dir = get_ontologies_dir()
    ontologies_dir.mkdir(parents=True, exist_ok=True)

    file_path = ontologies_dir / file.filename
    content = await file.read()

    # Write file temporarily
    with open(file_path, "wb") as f:
        f.write(content)

    # Validate ontology using validator
    result = validate_ontology(file_path)

    if not result.valid:
        file_path.unlink()  # Remove invalid file
        errors = "; ".join(result.errors)
        logger.warning(f"Invalid ontology upload {file.filename}: {errors}")
        raise HTTPException(status_code=400, detail=f"Invalid ontology: {errors}")

    if result.class_count == 0:
        file_path.unlink()
        raise HTTPException(status_code=400, detail="Ontology has no class definitions")

    # Register and cache
    registry = get_registry()
    cache = get_cache()

    dag = OntologyDAG(file_path)
    dag.build_dag()

    entry = registry.register(
        file.filename,
        class_count=len(dag.nodes),
    )

    tree = cache.build_from_dag(dag, entry.file_hash)
    cache.save(entry.id, tree)
    registry.update(entry.id, max_depth=tree.metadata.get("max_depth", 0))

    logger.info(f"Uploaded ontology {entry.id} ({file.filename}) with {len(dag.nodes)} classes")

    return {
        "id": entry.id,
        "filename": entry.filename,
        "class_count": len(dag.nodes),
        "warnings": result.warnings if result.warnings else None,
    }


@router.get("/{ontology_id}")
async def get_ontology(ontology_id: str):
    """Get ontology details."""
    try:
        resolved_id = resolve_ontology_id(ontology_id)
        registry = get_registry()
        entry = registry.get(resolved_id)

        if not entry:
            raise HTTPException(status_code=404, detail="Ontology not found")

        cache = get_cache()
        cached_tree = cache.load(resolved_id)

        return {
            "id": entry.id,
            "filename": entry.filename,
            "class_count": entry.class_count,
            "max_depth": entry.max_depth,
            "root": cached_tree.root if cached_tree else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading ontology: {e}") from None


@router.get("/{ontology_id}/tree", response_model=OntologyTree)
async def get_ontology_tree(
    ontology_id: str,
    depth: Annotated[int | None, Query(description="Max depth to load (lazy loading)")] = None,
    root: Annotated[str | None, Query(description="Root node URL for subtree")] = None,
):
    """Get ontology as tree structure.

    Args:
        ontology_id: Ontology ID or filename
        depth: Maximum depth to return (for lazy loading). None = full tree.
        root: Root node URL for subtree. None = tree root.
    """
    try:
        resolved_id = resolve_ontology_id(ontology_id)
        ensure_cached(resolved_id)

        cache = get_cache()
        cached_tree = cache.load(resolved_id)

        if not cached_tree:
            raise HTTPException(status_code=500, detail="Cache not available")

        # Get subtree if depth or root specified
        if depth is not None or root is not None:
            subtree = cached_tree.get_subtree(root_url=root, max_depth=depth)
            nodes = {
                url: OntologyNode(
                    url=node.url,
                    name=node.name,
                    label=node.label,
                    comment=node.comment,
                    children=node.children,
                    depth=node.depth,
                    has_more=node.has_more,
                )
                for url, node in subtree.nodes.items()
            }
            return OntologyTree(
                root=subtree.root,
                nodes=nodes,
                truncated=subtree.metadata.get("truncated", False),
                total_nodes=cached_tree.metadata.get("total_nodes", len(cached_tree.nodes)),
            )

        # Return full tree
        nodes = {
            url: OntologyNode(
                url=node.url,
                name=node.name,
                label=node.label,
                comment=node.comment,
                children=node.children,
                depth=node.depth,
                has_more=False,
            )
            for url, node in cached_tree.nodes.items()
        }

        return OntologyTree(
            root=cached_tree.root,
            nodes=nodes,
            truncated=False,
            total_nodes=len(nodes),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error building tree for {ontology_id}")
        raise HTTPException(status_code=500, detail=f"Error building tree: {e}") from None


@router.get("/{ontology_id}/classes")
async def get_ontology_classes(ontology_id: str, search: str = ""):
    """Get list of classes in ontology with optional search."""
    try:
        resolved_id = resolve_ontology_id(ontology_id)
        ensure_cached(resolved_id)

        cache = get_cache()
        cached_tree = cache.load(resolved_id)

        if not cached_tree:
            raise HTTPException(status_code=500, detail="Cache not available")

        classes = []
        for url, node in cached_tree.nodes.items():
            # Filter by search term
            if search:
                search_lower = search.lower()
                name_match = search_lower in node.name.lower()
                label_match = node.label and search_lower in node.label.lower()
                if not name_match and not label_match:
                    continue

            classes.append({
                "url": url,
                "name": node.name,
                "label": node.label,
                "comment": node.comment,
            })

        return {"classes": classes, "total": len(classes)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing classes: {e}") from None


@router.get("/{ontology_id}/validate")
async def validate_ontology_endpoint(ontology_id: str):
    """Validate an ontology file."""
    registry = get_registry()
    ontologies_dir = get_ontologies_dir()

    # Resolve ID to filename
    entry = registry.get(ontology_id) or registry.get_by_filename(ontology_id)

    file_path = ontologies_dir / entry.filename if entry else ontologies_dir / ontology_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ontology not found")

    result = validate_ontology(file_path)

    return {
        "id": entry.id if entry else ontology_id,
        "valid": result.valid,
        "class_count": result.class_count,
        "has_root": result.has_root,
        "errors": result.errors,
        "warnings": result.warnings,
    }


@router.delete("/{ontology_id}")
async def delete_ontology(ontology_id: str):
    """Delete an ontology."""
    registry = get_registry()
    cache = get_cache()
    ontologies_dir = get_ontologies_dir()

    # Resolve ID
    entry = registry.get(ontology_id) or registry.get_by_filename(ontology_id)

    if entry:
        file_path = ontologies_dir / entry.filename
        resolved_id = entry.id
    else:
        file_path = ontologies_dir / ontology_id
        resolved_id = ontology_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ontology not found")

    # Delete file
    file_path.unlink()

    # Remove from registry and cache
    if entry:
        registry.unregister(entry.id)
        cache.delete(entry.id)

    logger.info(f"Deleted ontology {resolved_id}")
    return {"message": "Ontology deleted successfully"}
