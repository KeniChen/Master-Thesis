#!/usr/bin/env python3
"""Migration script to create initial table registry from existing CSV files."""

import argparse
import sys
from pathlib import Path

# Add backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from saed.core.config.settings import get_absolute_path, load_config
from saed.core.table import TableRegistry


def main():
    """Run the migration."""
    parser = argparse.ArgumentParser(description="Initialize table registry")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip confirmation prompts (for automated setup)",
    )
    args = parser.parse_args()

    config = load_config()
    tables_dir = get_absolute_path(config.paths.tables)

    print(f"Tables directory: {tables_dir}")

    # Check if registry already exists
    registry_path = tables_dir / "registry.json"
    if registry_path.exists():
        print(f"Registry already exists at {registry_path}")
        if args.non_interactive:
            print("Overwriting (non-interactive mode)...")
        else:
            response = input("Overwrite? (y/N): ").strip().lower()
            if response != "y":
                print("Aborted.")
                return

        # Remove existing registry
        registry_path.unlink()

    # Create new registry and sync with directory
    registry = TableRegistry.load(tables_dir)
    result = registry.sync_with_directory()

    print(f"\nMigration completed:")
    print(f"  Added: {len(result['added'])} tables")
    print(f"  Removed: {len(result['removed'])} tables")
    print(f"  Updated: {len(result['updated'])} tables")

    # List all registered tables
    print(f"\nRegistered tables ({len(registry.tables)}):")
    for entry in sorted(registry.list_all(), key=lambda e: (e.category, e.filename)):
        print(f"  [{entry.id}] {entry.category}/{entry.filename} -> {entry.name}")


if __name__ == "__main__":
    main()
