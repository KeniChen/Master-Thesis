"""Single table annotation runner CLI (saed-run)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

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


class TerminalPrinter:
    """Handles terminal output for CLI progress display."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_time_ms = 0

    def print_config(
        self,
        table_id: str,
        table_name: str,
        ontology_id: str,
        class_count: int,
        columns: list[str],
        mode: str,
        prompt_type: str,
        max_depth: int,
        k: int,
        provider: str,
        model: str,
        output_dir: Path,
    ) -> None:
        """Print configuration summary."""
        print("\nConfiguration:")
        print(f"  Table: {table_id} ({table_name})")
        print(f"  Ontology: {ontology_id} ({class_count} classes)")
        print(f"  Columns: {', '.join(columns)}")
        print(f"  Mode: {mode} | Prompt: {prompt_type} | Depth: {max_depth} | K: {k}")
        print(f"  Provider: {provider} | Model: {model}")
        print(f"  Output: {output_dir}")
        print()

    def print_column_start(self, idx: int, total: int, column_name: str) -> None:
        """Print column start message."""
        print(f"[{idx}/{total}] Column: {column_name}")

    def print_step(self, step_data: dict[str, Any]) -> None:
        """Print a BFS step result."""
        if not self.verbose:
            return

        level = step_data.get("level", 0)
        parent = step_data.get("parent", "Root")
        candidates = step_data.get("candidates", [])
        selected = step_data.get("selected", [])
        status = step_data.get("status", "completed")

        # Get timing and token info (use 'or 0' to handle None values)
        llm_response = step_data.get("llm_response", {})
        latency_ms = (llm_response.get("latency_ms") or 0) if llm_response else 0
        tokens = (llm_response.get("total_tokens") or 0) if llm_response else 0
        input_tokens = (llm_response.get("input_tokens") or 0) if llm_response else 0
        output_tokens = (llm_response.get("output_tokens") or 0) if llm_response else 0

        # Accumulate totals
        self.total_time_ms += latency_ms
        self.total_tokens += tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # For EDM mode, sum up all agent tokens
        edm_result = step_data.get("edm_result")
        if edm_result:
            for agent in edm_result.get("agents", []):
                agent_resp = agent.get("llm_response", {})
                if agent_resp:
                    self.total_time_ms += agent_resp.get("latency_ms") or 0
                    self.total_tokens += agent_resp.get("total_tokens") or 0
                    self.total_input_tokens += agent_resp.get("input_tokens") or 0
                    self.total_output_tokens += agent_resp.get("output_tokens") or 0

        print(f"  Level {level}: {parent} -> {len(candidates)} candidates")

        if status == "failed":
            print(f"    x Failed: {step_data.get('error', 'Unknown error')}")
        elif selected:
            token_str = f", {tokens} tokens" if tokens else ""
            print(f"    > Selected: {', '.join(selected)} ({latency_ms}ms{token_str})")
        else:
            print(f"    - No selection ({latency_ms}ms)")

    def print_column_complete(
        self, column_name: str, final_paths: list[list[str]], status: str
    ) -> None:
        """Print column completion message."""
        if status == "completed":
            paths_str = " | ".join(["/".join(p) if p else "(empty)" for p in final_paths])
            print(f"  > Final: {paths_str}")
        elif status == "failed":
            print("  x Column failed")
        else:
            print("  ~ Partial completion")
        print()

    def print_summary(
        self,
        total_columns: int,
        completed_columns: int,
        elapsed_time: float,
        output_path: Path,
    ) -> None:
        """Print final summary."""
        print("Summary:")
        print(f"  Columns: {completed_columns}/{total_columns} completed")
        print(f"  Total time: {elapsed_time:.1f}s")
        if self.total_tokens:
            print(
                f"  Total tokens: {self.total_tokens:,} "
                f"(input: {self.total_input_tokens:,}, output: {self.total_output_tokens:,})"
            )
        print(f"  Results saved to: {output_path}")


def resolve_table(
    table_id: str, registry: TableRegistry, tables_dir: Path
) -> tuple[str, str, str, Path, list[str]]:
    """Resolve table ID to (registry_id, table_id, table_name, file_path, columns).

    Args:
        table_id: Table ID (registry hash ID) or filename
        registry: Table registry
        tables_dir: Tables directory

    Returns:
        Tuple of (registry_id, table_id, table_name, file_path, columns)

    Raises:
        ValueError: If table not found
    """
    # Try direct ID lookup
    entry = registry.get(table_id)
    if not entry:
        # Try by filename
        entry = registry.get_by_filename(table_id)

    if not entry:
        raise ValueError(f"Table not found: {table_id}")

    # Determine file path
    if entry.category and entry.category != "default":
        file_path = tables_dir / entry.category / entry.filename
    else:
        file_path = tables_dir / entry.filename

    return entry.id, entry.filename, entry.name, file_path, entry.columns


def resolve_ontology(
    ontology_id: str, registry: OntologyRegistry, ontologies_dir: Path
) -> tuple[str, str, Path]:
    """Resolve ontology ID to (registry_id, filename, file_path).

    Args:
        ontology_id: Ontology ID or filename
        registry: Ontology registry
        ontologies_dir: Ontologies directory

    Returns:
        Tuple of (registry_id, filename, file_path)

    Raises:
        ValueError: If ontology not found
    """
    # Try direct ID lookup
    entry = registry.get(ontology_id)
    if not entry:
        # Try by filename
        entry = registry.get_by_filename(ontology_id)

    if entry:
        return entry.id, entry.filename, ontologies_dir / entry.filename

    # If not in registry, try direct file path
    file_path = ontologies_dir / ontology_id
    if file_path.exists():
        return "", ontology_id, file_path

    raise ValueError(f"Ontology not found: {ontology_id}")


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


def run_single_table(
    config: Config,
    table_id: str,
    ontology_id: str,
    columns: list[str],
    mode: str,
    prompt_type: str,
    max_depth: int,
    k: int,
    output_dir: Path,
    verbose: bool = True,
) -> dict[str, Any]:
    """Run annotation on a single table.

    Returns:
        Run result dictionary
    """
    # Load registries
    tables_dir = get_absolute_path(config.paths.tables)
    ontologies_dir = get_absolute_path(config.paths.ontologies)

    table_registry = TableRegistry.load(tables_dir)
    table_registry.sync_with_directory()

    ontology_registry = OntologyRegistry.load(ontologies_dir)
    ontology_registry.sync_with_directory()

    # Resolve table and ontology
    table_registry_id, table_filename, table_name, table_path, all_columns = resolve_table(
        table_id, table_registry, tables_dir
    )
    ontology_registry_id, ontology_filename, ontology_path = resolve_ontology(
        ontology_id, ontology_registry, ontologies_dir
    )

    # Determine columns to process
    if not columns:
        columns = all_columns

    # Load ontology
    ontology_dag = OntologyDAG(str(ontology_path))
    ontology_dag.build_dag()

    # Load table and create markdown preview
    df = pd.read_csv(table_path)
    table_markdown = df.head(k).to_markdown(index=False)

    # Get provider and model info
    provider = config.llm.active_provider
    model = get_provider_model(provider, config)

    # Setup terminal printer
    printer = TerminalPrinter(verbose=verbose)

    # Print configuration
    printer.print_config(
        table_id=table_filename,
        table_name=table_name,
        ontology_id=ontology_filename,
        class_count=len(ontology_dag.nodes),
        columns=columns,
        mode=mode,
        prompt_type=prompt_type,
        max_depth=max_depth,
        k=k,
        provider=provider,
        model=model,
        output_dir=output_dir,
    )

    # Create run ID and ensure output directory exists
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create SSE callback for terminal output
    def terminal_callback(event_type: str, data: dict[str, Any]) -> None:
        if event_type == "step":
            printer.print_step(data.get("step", {}))

    # Create EDM options if needed
    edm_options = None
    if mode == "edm":
        edm_options = config.defaults.edm_options

    # Create executor
    executor = RunExecutor(
        config=config,
        mode=mode,
        prompt_type=prompt_type,
        edm_options=edm_options,
        max_depth=max_depth,
        k=k,
        sse_callback=terminal_callback,
    )

    # Execute annotation for each column
    start_time = time.time()
    columns_results: list[dict[str, Any]] = []
    completed_count = 0
    failed_count = 0

    for idx, column_name in enumerate(columns, start=1):
        printer.print_column_start(idx, len(columns), column_name)

        result = executor.execute_column(
            table_name=table_name,
            table_markdown=table_markdown,
            column_name=column_name,
            ontology_dag=ontology_dag,
            run_id=run_id,
        )

        columns_results.append(column_result_to_dict(result))

        if result.status == "completed":
            completed_count += 1
        else:
            failed_count += 1

        printer.print_column_complete(column_name, result.final_paths, result.status)

    elapsed_time = time.time() - start_time

    # Determine final status
    if failed_count == len(columns):
        final_status = "failed"
    elif failed_count > 0:
        final_status = "partial"
    else:
        final_status = "completed"

    # Build EDM options dict if used
    edm_options_dict = None
    if edm_options:
        edm_options_dict = {
            "classes_per_agent": edm_options.classes_per_agent,
            "agents_per_class": edm_options.agents_per_class,
            "consensus_threshold": edm_options.consensus_threshold,
        }

    # Build result (matching API format)
    result = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "status": final_status,
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
            "completed_columns": completed_count,
            "failed_columns": failed_count,
            "partial_columns": 0,  # CLI doesn't track partial status separately
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

    printer.print_summary(len(columns), completed_count, elapsed_time, output_path)

    return result


def main() -> None:
    """Main entry point for saed-run CLI."""
    parser = argparse.ArgumentParser(
        description="Run semantic annotation on a single table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Annotate specific columns
  saed-run --table 28.csv --ontology BEO.rdf --columns "Energy" "Temperature"

  # Annotate all columns
  saed-run --table 28.csv --ontology BEO.rdf --all-columns

  # Specify output directory
  saed-run --table 28.csv --ontology BEO.rdf --all-columns --output-dir experiments/exp001/

  # Use EDM mode with custom parameters
  saed-run --table 28.csv --ontology BEO.rdf --all-columns --mode edm --max-depth 4
        """,
    )

    parser.add_argument(
        "--table",
        type=str,
        required=True,
        help="Table filename or registry ID (e.g., 28.csv)",
    )
    parser.add_argument(
        "--ontology",
        type=str,
        required=True,
        help="Ontology filename or registry ID (e.g., BEO.rdf)",
    )
    parser.add_argument(
        "--columns",
        type=str,
        nargs="+",
        help="Column names to annotate",
    )
    parser.add_argument(
        "--all-columns",
        action="store_true",
        help="Annotate all columns in the table",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "edm"],
        help="Decision mode: single or edm (default: from config)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        choices=["direct", "cot"],
        help="Prompt type: direct or cot (default: from config)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum BFS depth (default: from config)",
    )
    parser.add_argument(
        "--k",
        type=int,
        help="Number of sample rows (default: from config)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (default: data/runs/)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=SUPPORTED_PROVIDERS,
        help="LLM provider (overrides config)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name (overrides config)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed step output",
    )

    args = parser.parse_args()

    # Validate column specification
    if not args.columns and not args.all_columns:
        parser.error("Must specify --columns or --all-columns")

    if args.columns and args.all_columns:
        parser.error("Cannot specify both --columns and --all-columns")

    # Load configuration
    config = load_config()

    # Apply provider/model overrides
    if args.provider:
        config.llm.active_provider = args.provider
    if args.model:
        provider_config = getattr(config.llm.providers, config.llm.active_provider)
        provider_config.default_model = args.model

    # Apply defaults
    mode = args.mode or config.defaults.mode
    prompt_type = args.prompt or config.defaults.prompt_type
    max_depth = args.max_depth or config.defaults.max_depth
    k = args.k or config.defaults.k

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = get_absolute_path(config.paths.runs)

    # Run annotation
    try:
        run_single_table(
            config=config,
            table_id=args.table,
            ontology_id=args.ontology,
            columns=args.columns or [],  # Empty list means all columns
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


if __name__ == "__main__":
    main()
