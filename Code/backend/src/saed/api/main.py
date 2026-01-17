"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from saed.api.routes import batches, config, evaluations, labels, llm, ontologies, runs, tables
from saed.core.batches import BatchRegistry
from saed.core.config.settings import get_absolute_path, load_config
from saed.core.labels import LabelsRegistry
from saed.core.ontology import OntologyRegistry
from saed.core.table import TableRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize registries on startup."""
    cfg = load_config()

    # Sync table registry
    tables_dir = get_absolute_path(cfg.paths.tables)
    if tables_dir.exists():
        table_registry = TableRegistry.load(tables_dir)
        result = table_registry.sync_with_directory()
        logger.info(
            f"Table registry synced: {len(result['added'])} added, "
            f"{len(result['removed'])} removed, {len(result['updated'])} updated"
        )

    # Sync ontology registry
    ontologies_dir = get_absolute_path(cfg.paths.ontologies)
    if ontologies_dir.exists():
        ontology_registry = OntologyRegistry.load(ontologies_dir)
        result = ontology_registry.sync_with_directory()
        logger.info(
            f"Ontology registry synced: {len(result['added'])} added, "
            f"{len(result['removed'])} removed, {len(result['updated'])} updated"
        )

    # Sync labels registry
    labels_dir = get_absolute_path(cfg.paths.labels)
    if labels_dir.exists():
        labels_registry = LabelsRegistry.load(labels_dir)
        result = labels_registry.sync_with_directory()
        logger.info(
            f"Labels registry synced: {len(result['added'])} added, "
            f"{len(result['removed'])} removed"
        )

    # Sync batches registry
    batches_dir = get_absolute_path(cfg.paths.batches)
    batches_dir.mkdir(parents=True, exist_ok=True)
    batch_registry = BatchRegistry.load(batches_dir)
    result = batch_registry.sync_with_directory()
    logger.info(
        f"Batch registry synced: {len(result['added'])} added, "
        f"{len(result['removed'])} removed"
    )

    yield


app = FastAPI(
    title="SAED API",
    description="Semantic Annotation with Ensemble Decision-making",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tables.router, prefix="/api/tables", tags=["tables"])
app.include_router(ontologies.router, prefix="/api/ontologies", tags=["ontologies"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(labels.router, prefix="/api/labels", tags=["labels"])
app.include_router(batches.router, prefix="/api/batches", tags=["batches"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


def main():
    """Run the API server."""
    uvicorn.run(
        "saed.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
