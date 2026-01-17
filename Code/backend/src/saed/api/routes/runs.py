"""Run management routes."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from saed.api.schemas import (
    AgentResult,
    BFSStep,
    ColumnResult,
    CreateRunRequest,
    CreateRunResponse,
    EDMResult,
    EvaluationMetrics,
    LLMRequest,
    LLMResponse,
    RunConfig,
    RunListItem,
    RunListResponse,
    RunResult,
    RunSummary,
    VoteSummary,
)
from saed.core.config.settings import EDMOptions, get_absolute_path, load_config
from saed.core.executor import RunExecutor
from saed.core.ontology import OntologyDAG, OntologyRegistry
from saed.core.table import TableRegistry

router = APIRouter()
logger = logging.getLogger(__name__)

# Store for active SSE connections (run_id -> list of queues)
active_streams: dict[str, list[asyncio.Queue]] = {}


def get_runs_dir() -> Path:
    """Get the runs directory path."""
    config = load_config()
    return get_absolute_path(config.paths.runs)


def get_tables_dir() -> Path:
    """Get the tables directory path."""
    config = load_config()
    return get_absolute_path(config.paths.tables)


def get_ontologies_dir() -> Path:
    """Get the ontologies directory path."""
    config = load_config()
    return get_absolute_path(config.paths.ontologies)


def get_table_registry() -> TableRegistry:
    """Get the table registry."""
    return TableRegistry.load(get_tables_dir())


def get_ontology_registry() -> OntologyRegistry:
    """Get the ontology registry."""
    return OntologyRegistry.load(get_ontologies_dir())


def resolve_table_id(table_id: str) -> tuple[str, Path, str]:
    """Resolve table ID to (registry_id, file_path, filename).

    Args:
        table_id: Table ID (registry hash ID) or filename

    Returns:
        Tuple of (registry_id, file_path, filename)

    Raises:
        HTTPException: If table not found
    """
    registry = get_table_registry()
    tables_dir = get_tables_dir()

    # Try direct ID lookup (hash ID like "9f6657ea")
    entry = registry.get(table_id)
    if entry:
        if entry.category and entry.category != "default":
            file_path = tables_dir / entry.category / entry.filename
        else:
            file_path = tables_dir / entry.filename
        return entry.id, file_path, entry.filename

    # Try by filename (e.g., "28.csv")
    entry = registry.get_by_filename(table_id)
    if entry:
        if entry.category and entry.category != "default":
            file_path = tables_dir / entry.category / entry.filename
        else:
            file_path = tables_dir / entry.filename
        return entry.id, file_path, entry.filename

    raise HTTPException(status_code=404, detail=f"Table not found: {table_id}")


def resolve_ontology_id(ontology_id: str) -> tuple[str, Path, str]:
    """Resolve ontology ID to (registry_id, file_path, filename).

    Args:
        ontology_id: Ontology ID (slug like "saref") or filename

    Returns:
        Tuple of (registry_id, file_path, filename)

    Raises:
        HTTPException: If ontology not found
    """
    registry = get_ontology_registry()
    ontologies_dir = get_ontologies_dir()

    # Try direct ID lookup (slug like "saref")
    entry = registry.get(ontology_id)
    if entry:
        return entry.id, ontologies_dir / entry.filename, entry.filename

    # Try by filename
    entry = registry.get_by_filename(ontology_id)
    if entry:
        return entry.id, ontologies_dir / entry.filename, entry.filename

    raise HTTPException(status_code=404, detail=f"Ontology not found: {ontology_id}")


def load_run(run_id: str) -> dict[str, Any]:
    """Load a run from JSON file."""
    runs_dir = get_runs_dir()
    file_path = runs_dir / f"{run_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    with open(file_path) as f:
        return json.load(f)


def save_run(run_id: str, data: dict[str, Any]) -> None:
    """Save a run to JSON file."""
    runs_dir = get_runs_dir()
    runs_dir.mkdir(parents=True, exist_ok=True)

    file_path = runs_dir / f"{run_id}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


@router.get("", response_model=RunListResponse)
async def list_runs():
    """List all runs."""
    runs_dir = get_runs_dir()
    runs = []

    if runs_dir.exists():
        for file in sorted(runs_dir.glob("*.json"), reverse=True):
            try:
                with open(file) as f:
                    data = json.load(f)

                # Get table name
                table_id = data.get("config", {}).get("table_id", "")
                table_name = table_id.rsplit(".", 1)[0] if table_id else ""

                evaluation = None
                if data.get("evaluation"):
                    evaluation = EvaluationMetrics(**data["evaluation"])

                runs.append(
                    RunListItem(
                        run_id=data["run_id"],
                        table_id=table_id,
                        table_name=table_name,
                        mode=data.get("config", {}).get("mode", "single"),
                        prompt_type=data.get("config", {}).get("prompt_type", "cot"),
                        column_count=len(data.get("config", {}).get("columns", [])),
                        status=data.get("status", "unknown"),
                        created_at=datetime.fromisoformat(data["created_at"]),
                        evaluation=evaluation,
                    )
                )
            except Exception:
                continue

    return RunListResponse(runs=runs)


async def emit_sse_event(run_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Emit an SSE event to all connected clients for a run."""
    if run_id not in active_streams:
        return

    event_data = json.dumps(data, default=str)
    message = f"event: {event_type}\ndata: {event_data}\n\n"

    # Send to all connected queues
    for queue in active_streams[run_id]:
        try:
            await queue.put(message)
        except Exception:
            pass  # Queue might be full or closed


def sse_callback_sync(run_id: str):
    """Create a synchronous SSE callback for the RunExecutor."""
    loop = asyncio.new_event_loop()

    def callback(event_type: str, data: dict[str, Any]) -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(emit_sse_event(run_id, event_type, data))

    return callback


async def execute_run_background(run_id: str, request: CreateRunRequest) -> None:
    """Execute the annotation run in background."""
    config = load_config()

    # Update status to running
    run_data = load_run(run_id)
    run_data["status"] = "running"
    save_run(run_id, run_data)

    await emit_sse_event(run_id, "run_start", {"run_id": run_id, "status": "running"})

    try:
        # Resolve and load table (handles both ID and filename, respects category subdirectories)
        _, table_path, table_filename = resolve_table_id(request.table_id)
        df = pd.read_csv(table_path)
        table_name = table_filename.rsplit(".", 1)[0]

        # Build table markdown (k rows)
        table_markdown = df.head(request.k).to_markdown(index=False)

        # Resolve and load ontology
        _, ontology_path, _ = resolve_ontology_id(request.ontology_id)
        if not ontology_path.exists():
            raise ValueError(f"Ontology not found: {request.ontology_id}")

        ontology_dag = OntologyDAG(str(ontology_path))
        ontology_dag.build_dag()

        # Create EDM options if provided
        edm_options = None
        if request.edm_options:
            edm_options = EDMOptions(**request.edm_options)

        # Create executor with async SSE callback
        async def sse_callback(event_type: str, data: dict[str, Any]) -> None:
            await emit_sse_event(run_id, event_type, data)

        executor = RunExecutor(
            config=config,
            mode=request.mode,
            prompt_type=request.prompt_type,
            edm_options=edm_options,
            max_depth=request.max_depth,
            k=request.k,
            async_sse_callback=sse_callback,
        )

        # Execute for each column
        columns_results: list[dict[str, Any]] = []
        completed_count = 0
        failed_count = 0
        partial_count = 0

        for idx, column_name in enumerate(request.columns):
            # Emit column start event
            await emit_sse_event(
                run_id,
                "column_start",
                {
                    "run_id": run_id,
                    "column_name": column_name,
                    "column_index": idx,
                    "total_columns": len(request.columns),
                },
            )

            # Execute column annotation (async for non-blocking LLM calls)
            column_result = await executor.execute_column_async(
                table_name=table_name,
                table_markdown=table_markdown,
                column_name=column_name,
                ontology_dag=ontology_dag,
                run_id=run_id,
            )

            # Convert to dict for storage
            column_dict = _column_result_to_dict(column_result)
            columns_results.append(column_dict)

            # Update counts
            if column_result.status == "completed":
                completed_count += 1
            elif column_result.status == "failed":
                failed_count += 1
            else:
                partial_count += 1

            # Emit column complete event
            await emit_sse_event(
                run_id,
                "column_complete",
                {
                    "run_id": run_id,
                    "column_name": column_name,
                    "final_paths": column_result.final_paths,
                    "status": column_result.status,
                },
            )

            # Save intermediate progress
            run_data = load_run(run_id)
            run_data["columns"] = columns_results
            run_data["summary"] = {
                "total_columns": len(request.columns),
                "completed_columns": completed_count,
                "failed_columns": failed_count,
                "partial_columns": partial_count,
            }
            save_run(run_id, run_data)

        # Determine final status
        if failed_count == len(request.columns):
            final_status = "failed"
        elif failed_count > 0 or partial_count > 0:
            final_status = "partial"
        else:
            final_status = "completed"

        # Save final result
        run_data = load_run(run_id)
        run_data["status"] = final_status
        run_data["completed_at"] = datetime.now().isoformat()
        run_data["columns"] = columns_results
        run_data["summary"] = {
            "total_columns": len(request.columns),
            "completed_columns": completed_count,
            "failed_columns": failed_count,
            "partial_columns": partial_count,
        }
        save_run(run_id, run_data)

        # Emit run complete event
        await emit_sse_event(
            run_id,
            "run_complete",
            {
                "run_id": run_id,
                "status": final_status,
                "summary": run_data["summary"],
            },
        )

    except Exception as e:
        logger.exception(f"Run {run_id} failed: {e}")
        run_data = load_run(run_id)
        run_data["status"] = "failed"
        run_data["error"] = str(e)
        run_data["completed_at"] = datetime.now().isoformat()
        save_run(run_id, run_data)

        await emit_sse_event(
            run_id,
            "error",
            {"run_id": run_id, "error": str(e), "recoverable": False},
        )


def _column_result_to_dict(result) -> dict[str, Any]:
    """Convert ColumnResultDetail to dictionary for JSON storage."""
    steps = []
    for step in result.steps:
        step_dict: dict[str, Any] = {
            "level": step.level,
            "parent": step.parent,
            "candidates": step.candidates,
            "selected": step.selected,
            "status": step.status,
            "error": step.error,
        }

        if step.llm_request:
            step_dict["llm_request"] = {
                "prompt": step.llm_request.prompt,
                "model": step.llm_request.model,
                "timestamp": step.llm_request.timestamp.isoformat() if step.llm_request.timestamp else None,
            }

        if step.llm_response:
            step_dict["llm_response"] = {
                "raw": step.llm_response.raw,
                "reasoning": step.llm_response.reasoning,
                "answer": step.llm_response.answer,
                "latency_ms": step.llm_response.latency_ms,
                "input_tokens": step.llm_response.input_tokens,
                "output_tokens": step.llm_response.output_tokens,
                "total_tokens": step.llm_response.total_tokens,
            }

        if step.edm_result:
            step_dict["edm_result"] = {
                "consensus_threshold": step.edm_result.consensus_threshold,
                "total_agents": step.edm_result.total_agents,
                "votes_summary": [
                    {
                        "class_name": v.class_name,
                        "vote_count": v.vote_count,
                        "total_agents": v.total_agents,
                        "percentage": v.percentage,
                        "selected": v.selected,
                    }
                    for v in step.edm_result.votes_summary
                ],
                "agents": [
                    {
                        "agent_id": a.agent_id,
                        "assigned_classes": a.assigned_classes,
                        "voted_classes": a.voted_classes,
                        "status": a.status,
                        "error": a.error,
                        "llm_request": (
                            {
                                "prompt": a.llm_request.prompt,
                                "model": a.llm_request.model,
                                "timestamp": a.llm_request.timestamp.isoformat() if a.llm_request.timestamp else None,
                            }
                            if a.llm_request
                            else None
                        ),
                        "llm_response": (
                            {
                                "raw": a.llm_response.raw,
                                "reasoning": a.llm_response.reasoning,
                                "answer": a.llm_response.answer,
                                "latency_ms": a.llm_response.latency_ms,
                                "input_tokens": a.llm_response.input_tokens,
                                "output_tokens": a.llm_response.output_tokens,
                                "total_tokens": a.llm_response.total_tokens,
                            }
                            if a.llm_response
                            else None
                        ),
                    }
                    for a in step.edm_result.agents
                ],
            }

        steps.append(step_dict)

    return {
        "column_name": result.column_name,
        "status": result.status,
        "steps": steps,
        "final_paths": result.final_paths,
        "error": result.error,
    }


@router.post("", response_model=CreateRunResponse)
async def create_run(request: CreateRunRequest, background_tasks: BackgroundTasks):
    """Create and start a new annotation run."""
    # Generate run ID
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Resolve and validate table exists (handles both hash ID and filename)
    table_registry_id, table_path, table_filename = resolve_table_id(request.table_id)
    if not table_path.exists():
        raise HTTPException(status_code=404, detail=f"Table file not found: {table_filename}")

    # Resolve and validate ontology exists (handles both slug ID and filename)
    ontology_registry_id, ontology_path, ontology_filename = resolve_ontology_id(request.ontology_id)
    if not ontology_path.exists():
        raise HTTPException(status_code=404, detail=f"Ontology file not found: {ontology_filename}")

    # Create run data (store resolved filenames for execution)
    run_data = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "status": "pending",
        "config": {
            "table_id": table_filename,  # Store filename for loading
            "table_registry_id": table_registry_id,  # Store registry ID for reference
            "ontology_id": ontology_filename,  # Store filename for loading
            "ontology_registry_id": ontology_registry_id,  # Store registry ID for reference
            "columns": request.columns,
            "mode": request.mode,
            "prompt_type": request.prompt_type,
            "max_depth": request.max_depth,
            "k": request.k,
            "edm_options": request.edm_options,
        },
        "columns": [],
        "summary": None,
        "evaluation": None,
        "error": None,
    }

    save_run(run_id, run_data)

    # Create modified request with resolved IDs for background execution
    resolved_request = CreateRunRequest(
        table_id=table_filename,
        ontology_id=ontology_filename,
        columns=request.columns,
        mode=request.mode,
        prompt_type=request.prompt_type,
        max_depth=request.max_depth,
        k=request.k,
        edm_options=request.edm_options,
    )

    # Start background execution with resolved filenames
    background_tasks.add_task(execute_run_background, run_id, resolved_request)

    return CreateRunResponse(run_id=run_id, status="pending")


def _parse_step_from_dict(step_data: dict[str, Any]) -> BFSStep:
    """Parse a BFSStep from dictionary data."""
    # Parse LLM request
    llm_request = None
    if step_data.get("llm_request"):
        req_data = step_data["llm_request"]
        llm_request = LLMRequest(
            prompt=req_data["prompt"],
            model=req_data["model"],
            timestamp=datetime.fromisoformat(req_data["timestamp"]) if req_data.get("timestamp") else None,
        )

    # Parse LLM response
    llm_response = None
    if step_data.get("llm_response"):
        resp_data = step_data["llm_response"]
        llm_response = LLMResponse(
            raw=resp_data["raw"],
            reasoning=resp_data.get("reasoning"),
            answer=resp_data["answer"],
            latency_ms=resp_data.get("latency_ms"),
            input_tokens=resp_data.get("input_tokens"),
            output_tokens=resp_data.get("output_tokens"),
            total_tokens=resp_data.get("total_tokens"),
        )

    # Parse EDM result
    edm_result = None
    if step_data.get("edm_result"):
        edm_data = step_data["edm_result"]
        votes_summary = [
            VoteSummary(
                class_name=v["class_name"],
                vote_count=v["vote_count"],
                total_agents=v["total_agents"],
                percentage=v["percentage"],
                selected=v["selected"],
            )
            for v in edm_data.get("votes_summary", [])
        ]

        agents = []
        for a in edm_data.get("agents", []):
            agent_req = None
            if a.get("llm_request"):
                agent_req = LLMRequest(
                    prompt=a["llm_request"]["prompt"],
                    model=a["llm_request"]["model"],
                    timestamp=datetime.fromisoformat(a["llm_request"]["timestamp"]) if a["llm_request"].get("timestamp") else None,
                )
            agent_resp = None
            if a.get("llm_response"):
                agent_resp = LLMResponse(
                    raw=a["llm_response"]["raw"],
                    reasoning=a["llm_response"].get("reasoning"),
                    answer=a["llm_response"]["answer"],
                    latency_ms=a["llm_response"].get("latency_ms"),
                    input_tokens=a["llm_response"].get("input_tokens"),
                    output_tokens=a["llm_response"].get("output_tokens"),
                    total_tokens=a["llm_response"].get("total_tokens"),
                )
            agents.append(
                AgentResult(
                    agent_id=a["agent_id"],
                    assigned_classes=a["assigned_classes"],
                    llm_request=agent_req,
                    llm_response=agent_resp,
                    voted_classes=a["voted_classes"],
                    status=a.get("status", "success"),
                    error=a.get("error"),
                )
            )

        edm_result = EDMResult(
            consensus_threshold=edm_data["consensus_threshold"],
            total_agents=edm_data["total_agents"],
            votes_summary=votes_summary,
            agents=agents,
        )

    return BFSStep(
        level=step_data["level"],
        parent=step_data["parent"],
        candidates=step_data["candidates"],
        selected=step_data["selected"],
        status=step_data.get("status", "completed"),
        error=step_data.get("error"),
        llm_request=llm_request,
        llm_response=llm_response,
        edm_result=edm_result,
    )


@router.get("/{run_id}", response_model=RunResult)
async def get_run(run_id: str):
    """Get run details."""
    data = load_run(run_id)

    columns = []
    for col_data in data.get("columns", []):
        steps = [_parse_step_from_dict(step) for step in col_data.get("steps", [])]
        columns.append(
            ColumnResult(
                column_name=col_data["column_name"],
                status=col_data.get("status", "pending"),
                steps=steps,
                final_paths=col_data.get("final_paths", []),
                error=col_data.get("error"),
            )
        )

    evaluation = None
    if data.get("evaluation"):
        evaluation = EvaluationMetrics(**data["evaluation"])

    summary = None
    if data.get("summary"):
        summary = RunSummary(**data["summary"])

    return RunResult(
        run_id=data["run_id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        status=data.get("status", "unknown"),
        config=RunConfig(**data["config"]),
        columns=columns,
        summary=summary,
        evaluation=evaluation,
        error=data.get("error"),
    )


@router.delete("/{run_id}")
async def delete_run(run_id: str):
    """Delete a run."""
    runs_dir = get_runs_dir()
    file_path = runs_dir / f"{run_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    file_path.unlink()
    return {"message": "Run deleted successfully"}


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    """Stream run progress via Server-Sent Events.

    This endpoint provides real-time updates for a running annotation task.

    Events:
    - run_start: Run has started
    - column_start: Started processing a column
    - step: BFS step completed (includes LLM details)
    - column_complete: Finished processing a column
    - run_complete: Run has completed
    - error: An error occurred
    """
    # Verify run exists
    runs_dir = get_runs_dir()
    file_path = runs_dir / f"{run_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    # Create queue for this client
    queue: asyncio.Queue = asyncio.Queue()

    # Register queue
    if run_id not in active_streams:
        active_streams[run_id] = []
    active_streams[run_id].append(queue)

    async def event_generator():
        try:
            # Send initial connection message
            yield f"event: connected\ndata: {json.dumps({'run_id': run_id})}\n\n"

            # Check current status
            data = load_run(run_id)
            current_status = data.get("status", "unknown")

            # If already completed, send final state and close
            if current_status in ("completed", "failed", "partial"):
                yield f"event: run_complete\ndata: {json.dumps({'run_id': run_id, 'status': current_status, 'summary': data.get('summary')})}\n\n"
                return

            # Stream events from queue
            while True:
                try:
                    # Wait for events with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message

                    # Check if run is complete
                    if "run_complete" in message or "error" in message:
                        break

                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"

        finally:
            # Cleanup: remove queue from active streams
            if run_id in active_streams and queue in active_streams[run_id]:
                active_streams[run_id].remove(queue)
                if not active_streams[run_id]:
                    del active_streams[run_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
