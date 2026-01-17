"""Evaluation script for semantic annotation predictions."""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from saed.core.config.settings import get_absolute_path, load_config
from saed.core.evaluator import node_level_f1_precision_recall, path_level_f1_precision_recall
from saed.core.labels import LabelsRegistry, load_labels_file, parse_labels_to_paths, paths_to_string


def compute_column_metrics(
    pred_paths: list[list[str]], gt_paths: list[list[str]]
) -> dict[str, float]:
    """Compute path-level and node-level metrics for a single column.

    Args:
        pred_paths: List of predicted paths
        gt_paths: List of ground truth paths

    Returns:
        Dict with path_precision, path_recall, path_f1,
        node_precision, node_recall, node_f1
    """
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


def print_metrics(
    level_name: str,
    macro_precision: float,
    macro_recall: float,
    macro_f1: float,
    micro_precision: float,
    micro_recall: float,
    micro_f1: float,
) -> str:
    """Format and print metrics for a given level."""
    lines = [
        f"  {level_name}:",
        f"    Macro  - P: {macro_precision:.4f} | R: {macro_recall:.4f} | F1: {macro_f1:.4f}",
        f"    Micro  - P: {micro_precision:.4f} | R: {micro_recall:.4f} | F1: {micro_f1:.4f}",
    ]
    output = "\n".join(lines)
    print(output)
    return output + "\n"


def main() -> None:
    """Run evaluation on semantic annotation predictions."""
    parser = argparse.ArgumentParser(
        description="Evaluate semantic annotation predictions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  saed-eval experiments/ollama_direct_single/batch_20251205_211024.json --labels ground_truth.csv
  saed-eval batch.json --labels gt.csv --format csv
  saed-eval batch.json --labels gt.csv --output-dir ./results/
        """,
    )
    parser.add_argument(
        "batch_file",
        type=str,
        help="Path to batch JSON file",
    )
    parser.add_argument(
        "--labels",
        type=str,
        required=True,
        help="Ground truth labels file (filename or path)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "csv", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (default: same as batch file)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output messages",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config()
    labels_dir = get_absolute_path(config.paths.labels)

    # Resolve batch file path
    batch_path = Path(args.batch_file)
    if not batch_path.is_absolute():
        batch_path = Path.cwd() / batch_path
    if not batch_path.exists():
        print(f"Error: Batch file not found: {batch_path}", file=sys.stderr)
        sys.exit(1)

    # Load batch data
    with open(batch_path, encoding="utf-8") as f:
        batch_data = json.load(f)

    run_id = batch_data.get("run_id", batch_path.stem)
    batch_config = batch_data.get("config", {})

    if not args.quiet:
        print(f"Evaluating: {run_id}")

    # Resolve labels file
    labels_registry = LabelsRegistry.load(labels_dir)
    labels_path = labels_registry.get_file_path(args.labels)

    if labels_path is None:
        # Try as direct path
        labels_path = Path(args.labels)
        if not labels_path.is_absolute():
            labels_path = labels_dir / args.labels
        if not labels_path.exists():
            print(f"Error: Labels file not found: {args.labels}", file=sys.stderr)
            sys.exit(1)

    if not args.quiet:
        print(f"  Labels: {labels_path.name}")

    # Load labels
    df_labels = load_labels_file(labels_path)

    # Build evaluation data from batch
    eval_columns = []
    tables = batch_data.get("tables", [])

    if not tables:
        print("Error: No tables found in batch file", file=sys.stderr)
        sys.exit(1)

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
                if not args.quiet:
                    print(f"  Warning: No labels for {table_id}:{column_name}")
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
        print("Error: No evaluation data could be built", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"  Columns: {evaluated_columns} evaluated, {skipped_columns} skipped")

    # Compute aggregate metrics
    eval_data_for_metrics = [
        {"pred_paths": c["pred_paths"], "gt_paths": c["gt_paths"]}
        for c in eval_columns
    ]

    path_metrics = path_level_f1_precision_recall(eval_data_for_metrics)
    node_metrics = node_level_f1_precision_recall(eval_data_for_metrics)

    # Print results
    if not args.quiet:
        print("\nMetrics:")
        print_metrics("Path-Level", *path_metrics)
        print_metrics("Node-Level", *node_metrics)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = batch_path.parent

    # Base filename
    base_name = batch_path.stem

    # Build output data structures
    metrics_data = {
        "run_id": run_id,
        "evaluated_at": datetime.now().isoformat(),
        "labels_id": labels_path.name,
        "config": {
            "ontology_id": batch_config.get("ontology_id", ""),
            "mode": batch_config.get("mode", ""),
            "prompt_type": batch_config.get("prompt_type", ""),
            "max_depth": batch_config.get("max_depth", 0),
            "k": batch_config.get("k", 0),
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
    }

    eval_data = {
        "run_id": run_id,
        "evaluated_at": datetime.now().isoformat(),
        "labels_id": labels_path.name,
        "columns": eval_columns,
    }

    # Write output files
    output_files = []

    if args.format in ("json", "all"):
        # Write metrics JSON
        metrics_path = output_dir / f"{base_name}_metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2, ensure_ascii=False)
        output_files.append(metrics_path)

        # Write eval JSON
        eval_path = output_dir / f"{base_name}_eval.json"
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(eval_data, f, indent=2, ensure_ascii=False)
        output_files.append(eval_path)

    if args.format in ("csv", "all"):
        # Write eval CSV
        csv_path = output_dir / f"{base_name}_eval.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
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
            ])
            for col in eval_columns:
                writer.writerow([
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
        output_files.append(csv_path)

    if not args.quiet:
        print("\nOutput files:")
        for f in output_files:
            print(f"  {f}")

    # Return summary for programmatic use
    return {
        "run_id": run_id,
        "path_macro_f1": path_metrics[2],
        "node_macro_f1": node_metrics[2],
        "evaluated_columns": evaluated_columns,
        "output_files": [str(f) for f in output_files],
    }


if __name__ == "__main__":
    main()
