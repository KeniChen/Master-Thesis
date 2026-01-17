#!/usr/bin/env python3
"""Migration script to create initial ontology registry from existing RDF/OWL files."""

import argparse
import sys
from pathlib import Path

# Add backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from saed.core.config.settings import get_absolute_path, load_config
from saed.core.ontology import OntologyRegistry


def main():
    """Run the migration."""
    parser = argparse.ArgumentParser(description="Initialize ontology registry")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip confirmation prompts (for automated setup)",
    )
    args = parser.parse_args()

    config = load_config()
    ontologies_dir = get_absolute_path(config.paths.ontologies)

    print(f"Ontologies directory: {ontologies_dir}")

    # Check if registry already exists
    registry_path = ontologies_dir / "registry.json"
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
    registry = OntologyRegistry.load(ontologies_dir)
    result = registry.sync_with_directory()

    print(f"\nMigration completed:")
    print(f"  Added: {len(result['added'])} ontologies")
    print(f"  Removed: {len(result['removed'])} ontologies")
    print(f"  Updated: {len(result['updated'])} ontologies")

    # List all registered ontologies
    print(f"\nRegistered ontologies ({len(registry.ontologies)}):")
    for entry in sorted(registry.list_all(), key=lambda e: e.filename):
        print(f"  [{entry.id}] {entry.filename} (classes: {entry.class_count}, depth: {entry.max_depth})")


if __name__ == "__main__":
    main()
