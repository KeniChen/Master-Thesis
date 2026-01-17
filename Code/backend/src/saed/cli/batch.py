"""Batch annotation runner CLI (saed-run-batch)."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from saed.core.config.settings import (
    SUPPORTED_PROVIDERS,
    Config,
    get_absolute_path,
    get_provider_model,
    load_config,
)
from saed.core.executor import ColumnResultDetail, RunExecutor
from saed.core.ontology import OntologyDAG, OntologyRegistry
from saed.core.table import TableRegistry


class BatchTerminalPrinter:
    """Handles terminal output for batch CLI progress display."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_time_ms = 0

    def print_batch_config(
        self,
        ontology_id: str,
        class_count: int,
        mode: str,
        prompt_type: str,
        max_depth: int,
        k: int,
        provider: str,
        model: str,
        total_tables: int,
        total_columns: int,
        output_dir: Path,
    ) -> None:
        """Print batch configuration summary."""
        print("\nBatch Run Configuration:")
        print(f"  Ontology: {ontology_id} ({class_count} classes)")
        print(f"  Mode: {mode} | Prompt: {prompt_type} | Depth: {max_depth} | K: {k}")
        print(f"  Provider: {provider} | Model: {model}")
        print(f"  Tasks: {total_tables} tables, {total_columns} columns total")
        print(f"  Output: {output_dir}")
        print()

    def print_table_start(
        self, idx: int, total: int, table_id: str, table_name: str, column_count: int
    ) -> None:
        """Print table start message."""
        print(f"[{idx}/{total}] Table: {table_id} - {table_name} ({column_count} columns)")

    def print_column_progress(
        self,
        idx: int,
        total: int,
        column_name: str,
        status: str,
        time_ms: int,
        tokens: int,
    ) -> None:
        """Print column progress (compact format for batch)."""
        if status == "completed":
            token_str = f", {tokens} tokens" if tokens else ""
            print(f"  [{idx}/{total}] {column_name} ... ok ({time_ms}ms{token_str})")
        else:
            print(f"  [{idx}/{total}] {column_name} ... {status}")

    def print_table_complete(
        self,
        completed: int,
        total: int,
        time_ms: int,
        tokens: int,
    ) -> None:
        """Print table completion message."""
        print(f"  Table complete: {completed}/{total} columns, {time_ms}ms, {tokens:,} tokens")
        print()

    def print_batch_summary(
        self,
        total_tables: int,
        completed_tables: int,
        total_columns: int,
        completed_columns: int,
        elapsed_time: float,
        output_path: Path,
    ) -> None:
        """Print final batch summary."""
        print("\nBatch Summary:")
        print(f"  Tables: {completed_tables}/{total_tables} completed")
        print(f"  Columns: {completed_columns}/{total_columns} completed")
        print(f"  Total time: {elapsed_time:.1f}s")
        if self.total_tokens:
            print(
                f"  Total tokens: {self.total_tokens:,} "
                f"(input: {self.total_input_tokens:,}, output: {self.total_output_tokens:,})"
            )
        print(f"  Results saved to: {output_path}")

    def accumulate_step_tokens(self, step_data: dict[str, Any]) -> tuple[int, int]:
        """Accumulate tokens from a step, return (time_ms, tokens)."""
        time_ms = 0
        tokens = 0

        llm_response = step_data.get("llm_response", {})
        if llm_response:
            time_ms += llm_response.get("latency_ms") or 0
            tokens += llm_response.get("total_tokens") or 0
            self.total_tokens += llm_response.get("total_tokens") or 0
            self.total_input_tokens += llm_response.get("input_tokens") or 0
            self.total_output_tokens += llm_response.get("output_tokens") or 0

        edm_result = step_data.get("edm_result")
        if edm_result:
            for agent in edm_result.get("agents", []):
                agent_resp = agent.get("llm_response", {})
                if agent_resp:
                    time_ms += agent_resp.get("latency_ms") or 0
                    tokens += agent_resp.get("total_tokens") or 0
                    self.total_tokens += agent_resp.get("total_tokens") or 0
                    self.total_input_tokens += agent_resp.get("input_tokens") or 0
                    self.total_output_tokens += agent_resp.get("output_tokens") or 0

        self.total_time_ms += time_ms
        return time_ms, tokens


def resolve_table(
    table_id: str, registry: TableRegistry, tables_dir: Path
) -> tuple[str, str, str, Path, list[str], str]:
    """Resolve table ID to (registry_id, table_id, table_name, file_path, columns, category).

    Returns:
        Tuple of (registry_id, table_id, table_name, file_path, columns, category)

    Raises:
        ValueError: If table not found
    """
    entry = registry.get(table_id) or registry.get_by_filename(table_id)

    if not entry:
        raise ValueError(f"Table not found: {table_id}")

    if entry.category and entry.category != "default":
        file_path = tables_dir / entry.category / entry.filename
    else:
        file_path = tables_dir / entry.filename

    return entry.id, entry.filename, entry.name, file_path, entry.columns, entry.category


def resolve_ontology(
    ontology_id: str, registry: OntologyRegistry, ontologies_dir: Path
) -> tuple[str, str, Path]:
    """Resolve ontology ID to (registry_id, filename, file_path)."""
    entry = registry.get(ontology_id) or registry.get_by_filename(ontology_id)

    if entry:
        return entry.id, entry.filename, ontologies_dir / entry.filename

    file_path = ontologies_dir / ontology_id
    if file_path.exists():
        return "", ontology_id, file_path

    raise ValueError(f"Ontology not found: {ontology_id}")


def expand_table_pattern(
    pattern: str, registry: TableRegistry
) -> list[tuple[str, str | None]]:
    """Expand a table pattern (supports glob).

    Args:
        pattern: Table pattern (e.g., "28.csv", "real/*.csv", "*.csv")
        registry: Table registry

    Returns:
        List of (table_id, category) tuples
    """
    if "*" not in pattern and "?" not in pattern:
        return [(pattern, None)]

    # Parse category/pattern format
    if "/" in pattern:
        category, file_pattern = pattern.split("/", 1)
    else:
        category, file_pattern = None, pattern

    matched = []
    for entry in registry.list_all(category=category):
        if fnmatch.fnmatch(entry.filename, file_pattern):
            matched.append((entry.filename, entry.category))

    return matched


def column_result_to_dict(result: ColumnResultDetail) -> dict[str, Any]:
    """Convert ColumnResultDetail to dictionary for JSON serialization."""
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
                "timestamp": step.llm_request.timestamp.isoformat()
                if step.llm_request.timestamp
                else None,
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
                                "timestamp": a.llm_request.timestamp.isoformat()
                                if a.llm_request.timestamp
                                else None,
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


def load_batch_config(config_path: Path) -> dict[str, Any]:
    """Load batch configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_batch(
    config: Config,
    tasks: list[dict[str, Any]],
    ontology_id: str,
    mode: str,
    prompt_type: str,
    max_depth: int,
    k: int,
    output_dir: Path,
    verbose: bool = True,
) -> dict[str, Any]:
    """Run batch annotation on multiple tables.

    Args:
        config: Application config
        tasks: List of task dicts with 'table' and 'columns' keys
        ontology_id: Ontology ID or filename
        mode: Decision mode (single/edm)
        prompt_type: Prompt type (direct/cot)
        max_depth: Max BFS depth
        k: Number of sample rows
        output_dir: Output directory
        verbose: Show detailed output

    Returns:
        Batch result dictionary
    """
    # Load registries
    tables_dir = get_absolute_path(config.paths.tables)
    ontologies_dir = get_absolute_path(config.paths.ontologies)

    table_registry = TableRegistry.load(tables_dir)
    table_registry.sync_with_directory()

    ontology_registry = OntologyRegistry.load(ontologies_dir)
    ontology_registry.sync_with_directory()

    # Resolve ontology
    ontology_registry_id, ontology_filename, ontology_path = resolve_ontology(
        ontology_id, ontology_registry, ontologies_dir
    )

    # Load ontology
    ontology_dag = OntologyDAG(str(ontology_path))
    ontology_dag.build_dag()

    # Expand tasks (handle glob patterns)
    expanded_tasks: list[tuple[str, list[str]]] = []
    for task in tasks:
        table_pattern = task["table"]
        columns_spec = task.get("columns", "all")

        matched_tables = expand_table_pattern(table_pattern, table_registry)
        for table_id, _ in matched_tables:
            if columns_spec == "all":
                expanded_tasks.append((table_id, []))  # Empty list means all columns
            else:
                expanded_tasks.append((table_id, columns_spec))

    # Count total columns
    total_columns = 0
    for table_id, columns in expanded_tasks:
        if columns:
            total_columns += len(columns)
        else:
            entry = table_registry.get_by_filename(table_id)
            if entry:
                total_columns += len(entry.columns)

    # Get provider and model info
    provider = config.llm.active_provider
    model = get_provider_model(provider, config)

    # Setup printer
    printer = BatchTerminalPrinter(verbose=verbose)

    printer.print_batch_config(
        ontology_id=ontology_filename,
        class_count=len(ontology_dag.nodes),
        mode=mode,
        prompt_type=prompt_type,
        max_depth=max_depth,
        k=k,
        provider=provider,
        model=model,
        total_tables=len(expanded_tasks),
        total_columns=total_columns,
        output_dir=output_dir,
    )

    # Create run ID and ensure output directory exists
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"batch_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create EDM options if needed
    edm_options = None
    edm_options_dict = None
    if mode == "edm":
        edm_options = config.defaults.edm_options
        edm_options_dict = {
            "classes_per_agent": edm_options.classes_per_agent,
            "agents_per_class": edm_options.agents_per_class,
            "consensus_threshold": edm_options.consensus_threshold,
        }

    # Create executor (no callback for batch - we handle output manually)
    executor = RunExecutor(
        config=config,
        mode=mode,
        prompt_type=prompt_type,
        edm_options=edm_options,
        max_depth=max_depth,
        k=k,
    )

    # Execute batch
    start_time = time.time()
    tables_results: list[dict[str, Any]] = []
    total_completed_columns = 0
    completed_tables = 0

    for table_idx, (table_id, columns_spec) in enumerate(expanded_tasks, start=1):
        try:
            table_registry_id, table_filename, table_name, table_path, all_columns, _ = resolve_table(
                table_id, table_registry, tables_dir
            )
        except ValueError as e:
            print(f"  Warning: {e}, skipping...")
            continue

        columns = columns_spec if columns_spec else all_columns

        printer.print_table_start(
            table_idx, len(expanded_tasks), table_filename, table_name, len(columns)
        )

        # Load table
        df = pd.read_csv(table_path)
        table_markdown = df.head(k).to_markdown(index=False)

        # Process each column
        columns_results: list[dict[str, Any]] = []
        table_completed = 0
        table_tokens = 0
        table_time_ms = 0

        for col_idx, column_name in enumerate(columns, start=1):
            col_start = time.time()

            result = executor.execute_column(
                table_name=table_name,
                table_markdown=table_markdown,
                column_name=column_name,
                ontology_dag=ontology_dag,
                run_id=run_id,
            )

            col_time_ms = int((time.time() - col_start) * 1000)
            result_dict = column_result_to_dict(result)
            columns_results.append(result_dict)

            # Calculate tokens for this column
            col_tokens = 0
            for step in result_dict.get("steps", []):
                _, tokens = printer.accumulate_step_tokens(step)
                col_tokens += tokens

            table_tokens += col_tokens
            table_time_ms += col_time_ms

            if result.status == "completed":
                table_completed += 1
                total_completed_columns += 1

            printer.print_column_progress(
                col_idx, len(columns), column_name, result.status, col_time_ms, col_tokens
            )

        printer.print_table_complete(table_completed, len(columns), table_time_ms, table_tokens)

        # Determine table status
        if table_completed == len(columns):
            table_status = "completed"
            completed_tables += 1
        elif table_completed == 0:
            table_status = "failed"
        else:
            table_status = "partial"

        # Build single-table result (API-compatible format)
        table_run_id = f"run_{timestamp}_{table_filename.replace('.csv', '')}"
        table_result = {
            "run_id": table_run_id,
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "status": table_status,
            "config": {
                "table_id": table_filename,
                "table_registry_id": table_registry_id,
                "ontology_id": ontology_filename,
                "ontology_registry_id": ontology_registry_id,
                "columns": columns,
                "mode": mode,
                "prompt_type": prompt_type,
                "max_depth": max_depth,
                "k": k,
                "edm_options": edm_options_dict,
                "provider": provider,
                "model": model,
            },
            "columns": columns_results,
            "summary": {
                "total_columns": len(columns),
                "completed_columns": table_completed,
                "failed_columns": len(columns) - table_completed,
                "partial_columns": 0,
                "total_time_ms": table_time_ms,
                "total_tokens": table_tokens,
                "total_input_tokens": 0,  # Not tracked per-table currently
                "total_output_tokens": 0,
            },
            "evaluation": None,
            "error": None,
        }

        # Save individual table result (frontend-compatible format)
        table_output_path = output_dir / f"{table_run_id}.json"
        with open(table_output_path, "w") as f:
            json.dump(table_result, f, indent=2, default=str)

        # Add to tables_results for batch summary
        tables_results.append({
            "table_id": table_filename,
            "table_registry_id": table_registry_id,
            "table_name": table_name,
            "run_file": f"{table_run_id}.json",
            "columns": columns_results,
            "summary": {
                "total_columns": len(columns),
                "completed_columns": table_completed,
                "total_time_ms": table_time_ms,
                "total_tokens": table_tokens,
            },
        })

    elapsed_time = time.time() - start_time

    # Determine final status
    if completed_tables == 0:
        final_status = "failed"
    elif completed_tables < len(expanded_tasks):
        final_status = "partial"
    else:
        final_status = "completed"

    # Build batch summary result
    result = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "status": final_status,
        "config": {
            "ontology_id": ontology_filename,
            "ontology_registry_id": ontology_registry_id,
            "mode": mode,
            "prompt_type": prompt_type,
            "max_depth": max_depth,
            "k": k,
            "edm_options": edm_options_dict,
            "provider": provider,
            "model": model,
        },
        "tables": tables_results,
        "summary": {
            "total_tables": len(expanded_tasks),
            "completed_tables": completed_tables,
            "total_columns": total_columns,
            "completed_columns": total_completed_columns,
            "total_time_ms": int(elapsed_time * 1000),
            "total_tokens": printer.total_tokens,
            "total_input_tokens": printer.total_input_tokens,
            "total_output_tokens": printer.total_output_tokens,
        },
        "evaluation": None,
        "error": None,
    }

    # Save result (flat format: output_dir/{run_id}.json)
    output_path = output_dir / f"{run_id}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    printer.print_batch_summary(
        len(expanded_tasks),
        completed_tables,
        total_columns,
        total_completed_columns,
        elapsed_time,
        output_path,
    )

    return result


def cmd_config(args: argparse.Namespace) -> None:
    """Handle 'config' subcommand."""
    config_path = Path(args.config_file)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Load batch config
    batch_config = load_batch_config(config_path)

    # Load app config
    app_config = load_config()

    # Apply provider/model overrides
    if args.provider:
        app_config.llm.active_provider = args.provider
    if args.model:
        provider_config = getattr(app_config.llm.providers, app_config.llm.active_provider)
        provider_config.default_model = args.model

    # Extract parameters from batch config
    ontology_id = batch_config.get("ontology")
    if not ontology_id:
        print("Error: 'ontology' is required in config file", file=sys.stderr)
        sys.exit(1)

    tasks = batch_config.get("tasks", [])
    if not tasks:
        print("Error: 'tasks' is required in config file", file=sys.stderr)
        sys.exit(1)

    mode = batch_config.get("mode", app_config.defaults.mode)
    prompt_type = batch_config.get("prompt_type", app_config.defaults.prompt_type)
    max_depth = batch_config.get("max_depth", app_config.defaults.max_depth)
    k = batch_config.get("k", app_config.defaults.k)

    # Output directory: CLI arg > config file's directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = config_path.parent

    try:
        run_batch(
            config=app_config,
            tasks=tasks,
            ontology_id=ontology_id,
            mode=mode,
            prompt_type=prompt_type,
            max_depth=max_depth,
            k=k,
            output_dir=output_dir,
            verbose=not args.quiet,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    """Handle 'run' subcommand."""
    app_config = load_config()

    # Apply provider/model overrides
    if args.provider:
        app_config.llm.active_provider = args.provider
    if args.model:
        provider_config = getattr(app_config.llm.providers, app_config.llm.active_provider)
        provider_config.default_model = args.model

    # Build tasks from command line
    tables_dir = get_absolute_path(app_config.paths.tables)
    table_registry = TableRegistry.load(tables_dir)
    table_registry.sync_with_directory()

    tasks = []

    if args.tables:
        for table_id in args.tables:
            tasks.append({
                "table": table_id,
                "columns": "all" if args.all_columns else args.columns,
            })
    elif args.category:
        # Get all tables in category
        for entry in table_registry.list_all(category=args.category):
            tasks.append({
                "table": entry.filename,
                "columns": "all" if args.all_columns else args.columns,
            })

    if not tasks:
        print("Error: No tables specified. Use --tables or --category", file=sys.stderr)
        sys.exit(1)

    if not args.all_columns and not args.columns:
        print("Error: Must specify --columns or --all-columns", file=sys.stderr)
        sys.exit(1)

    mode = args.mode or app_config.defaults.mode
    prompt_type = args.prompt or app_config.defaults.prompt_type
    max_depth = args.max_depth or app_config.defaults.max_depth
    k = args.k or app_config.defaults.k

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = get_absolute_path(app_config.paths.runs)

    try:
        run_batch(
            config=app_config,
            tasks=tasks,
            ontology_id=args.ontology,
            mode=mode,
            prompt_type=prompt_type,
            max_depth=max_depth,
            k=k,
            output_dir=output_dir,
            verbose=not args.quiet,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for saed-run-batch CLI."""
    parser = argparse.ArgumentParser(
        description="Run batch semantic annotation on multiple tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # 'config' subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="Run batch from YAML config file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example config file (batch.yaml):
  ontology: BEO.rdf
  mode: single
  prompt_type: cot
  max_depth: 3
  k: 5
  tasks:
    - table: 28.csv
      columns: [Energy, Temperature]
    - table: 29.csv
      columns: all
    - table: real/*.csv
      columns: all

Example usage:
  saed-run-batch config experiments/exp001/batch.yaml
        """,
    )
    config_parser.add_argument(
        "config_file",
        type=str,
        help="Path to YAML config file",
    )
    config_parser.add_argument(
        "--provider",
        type=str,
        choices=SUPPORTED_PROVIDERS,
        help="LLM provider (overrides config)",
    )
    config_parser.add_argument(
        "--model",
        type=str,
        help="Model name (overrides config)",
    )
    config_parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (default: config file's directory)",
    )
    config_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output",
    )

    # 'run' subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Run batch from command line arguments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run multiple tables
  saed-run-batch run --tables 28.csv 29.csv --ontology BEO.rdf --all-columns

  # Run all tables in a category
  saed-run-batch run --category real --ontology BEO.rdf --all-columns

  # Specify output directory
  saed-run-batch run --tables 28.csv --ontology BEO.rdf --all-columns \\
    --output-dir experiments/exp001/
        """,
    )
    run_parser.add_argument(
        "--tables",
        type=str,
        nargs="+",
        help="Table filenames or IDs (supports glob patterns)",
    )
    run_parser.add_argument(
        "--category",
        type=str,
        help="Run all tables in this category (e.g., 'real', 'synthetic')",
    )
    run_parser.add_argument(
        "--ontology",
        type=str,
        required=True,
        help="Ontology filename or ID",
    )
    run_parser.add_argument(
        "--columns",
        type=str,
        nargs="+",
        help="Column names to annotate (for all tables)",
    )
    run_parser.add_argument(
        "--all-columns",
        action="store_true",
        help="Annotate all columns in each table",
    )
    run_parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "edm"],
        help="Decision mode (default: from config)",
    )
    run_parser.add_argument(
        "--prompt",
        type=str,
        choices=["direct", "cot"],
        help="Prompt type (default: from config)",
    )
    run_parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum BFS depth (default: from config)",
    )
    run_parser.add_argument(
        "--k",
        type=int,
        help="Number of sample rows (default: from config)",
    )
    run_parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (default: data/runs/)",
    )
    run_parser.add_argument(
        "--provider",
        type=str,
        choices=SUPPORTED_PROVIDERS,
        help="LLM provider (overrides config)",
    )
    run_parser.add_argument(
        "--model",
        type=str,
        help="Model name (overrides config)",
    )
    run_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output",
    )

    args = parser.parse_args()

    if args.command == "config":
        cmd_config(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
