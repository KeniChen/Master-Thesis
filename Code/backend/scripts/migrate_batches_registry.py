#!/usr/bin/env python3
"""Migration script to create initial batch registry from existing JSON files."""

import argparse
import sys
from pathlib import Path

# Add backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from saed.core.batches import BatchRegistry
from saed.core.config.settings import get_absolute_path, load_config


def main():
    """Run the migration."""
    parser = argparse.ArgumentParser(description="Initialize batch registry")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip confirmation prompts (for automated setup)",
    )
    args = parser.parse_args()

    config = load_config()
    batches_dir = get_absolute_path(config.paths.batches)

    # Ensure directory exists
    batches_dir.mkdir(parents=True, exist_ok=True)

    print(f"Batches directory: {batches_dir}")

    # Check if registry already exists
    registry_path = batches_dir / "registry.json"
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
    registry = BatchRegistry.load(batches_dir)
    result = registry.sync_with_directory()

    print(f"\nMigration completed:")
    print(f"  Added: {len(result['added'])} batches")
    print(f"  Removed: {len(result['removed'])} batches")

    # List all registered batches
    print(f"\nRegistered batches ({len(registry.batches)}):")
    for entry in sorted(registry.list_all(), key=lambda e: e.filename):
        print(f"  [{entry.id}] {entry.filename} (tables: {entry.total_tables}, columns: {entry.total_columns})")


if __name__ == "__main__":
    main()
