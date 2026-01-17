"""Evaluation routes for computing metrics on batch results."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from saed.core.config.settings import get_absolute_path, load_config
from saed.core.evaluator import node_level_f1_precision_recall, path_level_f1_precision_recall
from saed.core.labels import LabelsRegistry, load_labels_file, parse_labels_to_paths, paths_to_string

logger = logging.getLogger(__name__)

router = APIRouter()


def get_labels_dir() -> Path:
    """Get the labels directory path."""
    config = load_config()
    return get_absolute_path(config.paths.labels)


def get_labels_registry() -> LabelsRegistry:
    """Get or create the labels registry."""
    labels_dir = get_labels_dir()
    return LabelsRegistry.load(labels_dir)


def compute_column_metrics(
    pred_paths: list[list[str]], gt_paths: list[list[str]]
) -> dict[str, float]:
    """Compute path-level and node-level metrics for a single column."""
    # Path-level metrics
    pred_set = {tuple(p) for p in pred_paths}
    gt_set = {tuple(p) for p in gt_paths}

    path_tp = len(pred_set.intersection(gt_set))
    path_fp = len(pred_set - gt_set)
    path_fn = len(gt_set - pred_set)

    path_precision = path_tp / (path_tp + path_fp) if (path_tp + path_fp) > 0 else 0.0
    path_recall = path_tp / (path_tp + path_fn) if (path_tp + path_fn) > 0 else 0.0
    path_f1 = (
        2 * (path_precision * path_recall) / (path_precision + path_recall)
        if (path_precision + path_recall) > 0
        else 0.0
    )

    # Node-level metrics
    pred_nodes = set()
    for path in pred_paths:
        pred_nodes.update(path)

    gt_nodes = set()
    for path in gt_paths:
        gt_nodes.update(path)

    node_tp = len(pred_nodes.intersection(gt_nodes))
    node_fp = len(pred_nodes - gt_nodes)
    node_fn = len(gt_nodes - pred_nodes)

    node_precision = node_tp / (node_tp + node_fp) if (node_tp + node_fp) > 0 else 0.0
    node_recall = node_tp / (node_tp + node_fn) if (node_tp + node_fn) > 0 else 0.0
    node_f1 = (
        2 * (node_precision * node_recall) / (node_precision + node_recall)
        if (node_precision + node_recall) > 0
        else 0.0
    )

    return {
        "path_precision": round(path_precision, 4),
        "path_recall": round(path_recall, 4),
        "path_f1": round(path_f1, 4),
        "node_precision": round(node_precision, 4),
        "node_recall": round(node_recall, 4),
        "node_f1": round(node_f1, 4),
    }


class EvaluateRequest(BaseModel):
    """Request to run an evaluation."""

    batch_path: str  # Path to batch JSON file (relative to project root or absolute)
    labels_id: str  # Labels ID or filename


class CompareRequest(BaseModel):
    """Request to compare multiple evaluations."""

    batch_paths: list[str]  # Paths to batch JSON files
    labels_id: str  # Labels ID or filename


@router.post("")
async def run_evaluation(request: EvaluateRequest) -> dict[str, Any]:
    """Run evaluation on a batch result file.

    Returns full evaluation results including per-column metrics.
    """
    config = load_config()
    batches_dir = get_absolute_path(config.paths.batches)

    # Resolve batch file path
    batch_path = Path(request.batch_path)
    if not batch_path.is_absolute():
        batch_path = batches_dir / batch_path
    if not batch_path.exists():
        raise HTTPException(status_code=404, detail=f"Batch file not found: {request.batch_path}")

    # Load batch data
    try:
        with open(batch_path, encoding="utf-8") as f:
            batch_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading batch file: {e}") from None

    run_id = batch_data.get("run_id", batch_path.stem)
    batch_config = batch_data.get("config", {})

    # Resolve labels file
    labels_dir = get_labels_dir()
    labels_registry = get_labels_registry()
    labels_path = labels_registry.get_file_path(request.labels_id)

    if labels_path is None:
        # Try as direct path
        labels_path = Path(request.labels_id)
        if not labels_path.is_absolute():
            labels_path = labels_dir / request.labels_id
        if not labels_path.exists():
            raise HTTPException(status_code=404, detail=f"Labels file not found: {request.labels_id}")

    # Load labels
    try:
        df_labels = load_labels_file(labels_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading labels file: {e}") from None

    # Build evaluation data from batch
    eval_columns = []
    tables = batch_data.get("tables", [])

    if not tables:
        raise HTTPException(status_code=400, detail="No tables found in batch file")

    total_columns = 0
    evaluated_columns = 0
    skipped_columns = 0

    for table_data in tables:
        table_id = table_data.get("table_id", "")
        table_name = table_data.get("table_name", "")

        for col_idx, col_data in enumerate(table_data.get("columns", [])):
            total_columns += 1
            column_name = col_data.get("column_name", "")
            pred_paths = col_data.get("final_paths", [])

            # Get ground truth for this column
            mask = (df_labels["table_id"] == table_id) & (
                (df_labels["column_id"] == col_idx) | (df_labels["column_name"] == column_name)
            )

            if not mask.any():
                skipped_columns += 1
                continue

            label_row = df_labels[mask].iloc[0]
            gt_paths = parse_labels_to_paths(label_row)

            # Compute column metrics
            metrics = compute_column_metrics(pred_paths, gt_paths)

            eval_columns.append({
                "table_id": table_id,
                "table_name": table_name,
                "column_id": col_idx,
                "column_name": column_name,
                "pred_paths": pred_paths,
                "gt_paths": gt_paths,
                **metrics,
            })
            evaluated_columns += 1

    if not eval_columns:
        raise HTTPException(status_code=400, detail="No columns could be matched with ground truth")

    # Compute aggregate metrics
    eval_data_for_metrics = [
        {"pred_paths": c["pred_paths"], "gt_paths": c["gt_paths"]}
        for c in eval_columns
    ]

    path_metrics = path_level_f1_precision_recall(eval_data_for_metrics)
    node_metrics = node_level_f1_precision_recall(eval_data_for_metrics)

    return {
        "run_id": run_id,
        "evaluated_at": datetime.now().isoformat(),
        "labels_id": labels_path.name,
        "config": {
            "ontology_id": batch_config.get("ontology_id", ""),
            "mode": batch_config.get("mode", ""),
            "prompt_type": batch_config.get("prompt_type", ""),
            "max_depth": batch_config.get("max_depth", 0),
            "k": batch_config.get("k", 0),
            "provider": batch_config.get("provider", ""),
            "model": batch_config.get("model", ""),
        },
        "summary": {
            "total_tables": len(tables),
            "total_columns": total_columns,
            "evaluated_columns": evaluated_columns,
            "skipped_columns": skipped_columns,
        },
        "metrics": {
            "path_level": {
                "macro_precision": round(path_metrics[0], 4),
                "macro_recall": round(path_metrics[1], 4),
                "macro_f1": round(path_metrics[2], 4),
                "micro_precision": round(path_metrics[3], 4),
                "micro_recall": round(path_metrics[4], 4),
                "micro_f1": round(path_metrics[5], 4),
            },
            "node_level": {
                "macro_precision": round(node_metrics[0], 4),
                "macro_recall": round(node_metrics[1], 4),
                "macro_f1": round(node_metrics[2], 4),
                "micro_precision": round(node_metrics[3], 4),
                "micro_recall": round(node_metrics[4], 4),
                "micro_f1": round(node_metrics[5], 4),
            },
        },
        "performance": {
            "total_time_ms": batch_data.get("summary", {}).get("total_time_ms", 0),
            "avg_time_per_column_ms": (
                batch_data.get("summary", {}).get("total_time_ms", 0) // evaluated_columns
                if evaluated_columns > 0
                else 0
            ),
            "total_tokens": batch_data.get("summary", {}).get("total_tokens", 0),
        },
        "columns": eval_columns,
    }


@router.post("/compare")
async def compare_evaluations(request: CompareRequest) -> dict[str, Any]:
    """Compare multiple batch results against the same ground truth.

    Returns summary metrics for each batch for easy comparison.
    """
    if len(request.batch_paths) < 2:
        raise HTTPException(status_code=400, detail="At least 2 batch files required for comparison")

    results = []
    for batch_path in request.batch_paths:
        try:
            eval_request = EvaluateRequest(batch_path=batch_path, labels_id=request.labels_id)
            eval_result = await run_evaluation(eval_request)

            results.append({
                "run_id": eval_result["run_id"],
                "batch_path": batch_path,
                "config": eval_result["config"],
                "summary": eval_result["summary"],
                "metrics": eval_result["metrics"],
                "performance": eval_result["performance"],
            })
        except HTTPException as e:
            results.append({
                "batch_path": batch_path,
                "error": e.detail,
            })

    # Find best scores
    valid_results = [r for r in results if "error" not in r]

    best_path_f1 = None
    best_node_f1 = None
    if valid_results:
        best_path_f1 = max(r["metrics"]["path_level"]["macro_f1"] for r in valid_results)
        best_node_f1 = max(r["metrics"]["node_level"]["macro_f1"] for r in valid_results)

    return {
        "compared_at": datetime.now().isoformat(),
        "labels_id": request.labels_id,
        "total_batches": len(request.batch_paths),
        "successful": len(valid_results),
        "failed": len(results) - len(valid_results),
        "best_scores": {
            "path_macro_f1": best_path_f1,
            "node_macro_f1": best_node_f1,
        },
        "results": results,
    }


@router.get("/csv")
async def get_evaluation_csv(
    batch_path: str,
    labels_id: str,
) -> dict[str, Any]:
    """Get evaluation results as CSV-formatted data.

    Returns headers and rows suitable for CSV export.
    """
    # Run evaluation first
    eval_request = EvaluateRequest(batch_path=batch_path, labels_id=labels_id)
    eval_result = await run_evaluation(eval_request)

    # Build CSV data
    headers = [
        "table_id",
        "table_name",
        "column_id",
        "column_name",
        "pred_paths",
        "gt_paths",
        "path_precision",
        "path_recall",
        "path_f1",
        "node_precision",
        "node_recall",
        "node_f1",
    ]

    rows = []
    for col in eval_result["columns"]:
        rows.append([
            col["table_id"],
            col["table_name"],
            col["column_id"],
            col["column_name"],
            paths_to_string(col["pred_paths"]),
            paths_to_string(col["gt_paths"]),
            col["path_precision"],
            col["path_recall"],
            col["path_f1"],
            col["node_precision"],
            col["node_recall"],
            col["node_f1"],
        ])

    return {
        "run_id": eval_result["run_id"],
        "headers": headers,
        "rows": rows,
    }
