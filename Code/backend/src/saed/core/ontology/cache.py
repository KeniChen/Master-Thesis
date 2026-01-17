"""Ontology tree cache for pre-parsed structures."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from saed.core.ontology.dag import OntologyDAG

logger = logging.getLogger(__name__)


@dataclass
class CachedNode:
    """A cached ontology node with pre-computed depth."""

    url: str
    name: str
    label: str | None
    comment: str | None
    children: list[str]
    depth: int
    has_more: bool = False  # For lazy loading: indicates if node has unloaded children

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "name": self.name,
            "label": self.label,
            "comment": self.comment,
            "children": self.children,
            "depth": self.depth,
            "has_more": self.has_more,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CachedNode":
        """Create from dictionary."""
        return cls(
            url=data["url"],
            name=data["name"],
            label=data.get("label"),
            comment=data.get("comment"),
            children=data.get("children", []),
            depth=data.get("depth", 0),
            has_more=data.get("has_more", False),
        )


@dataclass
class CachedTree:
    """A cached ontology tree."""

    root: str
    nodes: dict[str, CachedNode]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "root": self.root,
            "nodes": {url: node.to_dict() for url, node in self.nodes.items()},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CachedTree":
        """Create from dictionary."""
        nodes = {
            url: CachedNode.from_dict(node_data)
            for url, node_data in data.get("nodes", {}).items()
        }
        return cls(
            root=data["root"],
            nodes=nodes,
            metadata=data.get("metadata", {}),
        )

    def get_subtree(
        self,
        root_url: str | None = None,
        max_depth: int | None = None,
    ) -> "CachedTree":
        """Get a subtree with optional depth limit.

        Args:
            root_url: Root node URL for subtree (None = use tree root)
            max_depth: Maximum depth to include (None = unlimited)

        Returns:
            New CachedTree with subset of nodes
        """
        start_url = root_url or self.root
        if start_url not in self.nodes and start_url != self.root:
            # Handle root (owl:Thing) which may not be in nodes
            start_url = self.root

        # BFS to collect nodes up to max_depth
        result_nodes: dict[str, CachedNode] = {}
        queue: list[tuple[str, int]] = [(start_url, 0)]
        visited = set()

        while queue:
            url, relative_depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            node = self.nodes.get(url)
            if node is None:
                continue

            # Check depth limit
            at_depth_limit = max_depth is not None and relative_depth >= max_depth

            # Create node copy, potentially with truncated children
            if at_depth_limit:
                # At depth limit: mark has_more if there are children
                result_nodes[url] = CachedNode(
                    url=node.url,
                    name=node.name,
                    label=node.label,
                    comment=node.comment,
                    children=[],  # Don't include children at limit
                    depth=node.depth,
                    has_more=len(node.children) > 0,
                )
            else:
                # Add children to queue
                for child_url in node.children:
                    if child_url not in visited:
                        queue.append((child_url, relative_depth + 1))

                # Check if any children will be truncated
                has_more = False
                if max_depth is not None:
                    for child_url in node.children:
                        child = self.nodes.get(child_url)
                        if child and len(child.children) > 0 and relative_depth + 1 >= max_depth:
                            # Child has grandchildren that might be truncated
                            has_more = True
                            break

                result_nodes[url] = CachedNode(
                    url=node.url,
                    name=node.name,
                    label=node.label,
                    comment=node.comment,
                    children=node.children,
                    depth=node.depth,
                    has_more=has_more,
                )

        return CachedTree(
            root=start_url,
            nodes=result_nodes,
            metadata={
                **self.metadata,
                "truncated": max_depth is not None and len(result_nodes) < len(self.nodes),
                "subtree_root": start_url,
                "max_depth": max_depth,
            },
        )


class OntologyCache:
    """Cache manager for ontology trees."""

    def __init__(self, cache_dir: Path):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, ontology_id: str) -> Path:
        """Get cache file path for an ontology."""
        return self.cache_dir / f"{ontology_id}.json"

    def exists(self, ontology_id: str) -> bool:
        """Check if cache exists for an ontology."""
        return self._cache_path(ontology_id).exists()

    def load(self, ontology_id: str) -> CachedTree | None:
        """Load cached tree from file.

        Args:
            ontology_id: Ontology ID

        Returns:
            CachedTree or None if not found
        """
        cache_path = self._cache_path(ontology_id)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            return CachedTree.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load cache for {ontology_id}: {e}")
            return None

    def save(self, ontology_id: str, tree: CachedTree) -> None:
        """Save tree to cache file.

        Args:
            ontology_id: Ontology ID
            tree: CachedTree to save
        """
        cache_path = self._cache_path(ontology_id)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(tree.to_dict(), f, ensure_ascii=False)
        logger.debug(f"Saved cache for {ontology_id}")

    def delete(self, ontology_id: str) -> bool:
        """Delete cache for an ontology.

        Args:
            ontology_id: Ontology ID

        Returns:
            True if deleted, False if not found
        """
        cache_path = self._cache_path(ontology_id)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Deleted cache for {ontology_id}")
            return True
        return False

    def build_from_dag(
        self,
        dag: OntologyDAG,
        source_hash: str = "",
    ) -> CachedTree:
        """Build CachedTree from OntologyDAG.

        Args:
            dag: Parsed OntologyDAG
            source_hash: Hash of source file for cache validation

        Returns:
            CachedTree with pre-computed depths
        """
        # Pre-compute depths using BFS from root
        depths: dict[str, int] = {}
        queue: list[tuple[str, int]] = [(dag.root, 0)]
        visited = set()

        while queue:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            depths[url] = depth

            # Add children
            for child_url in dag.edges_subclassof.get(url, []):
                if child_url not in visited:
                    queue.append((child_url, depth + 1))

        # Build nodes
        nodes: dict[str, CachedNode] = {}
        max_depth = 0

        for url, ontology_class in dag.nodes.items():
            depth = depths.get(url, 0)
            max_depth = max(max_depth, depth)

            children = dag.edges_subclassof.get(url, [])
            nodes[url] = CachedNode(
                url=url,
                name=ontology_class.name,
                label=ontology_class.label,
                comment=ontology_class.comment,
                children=children,
                depth=depth,
                has_more=False,
            )

        return CachedTree(
            root=dag.root,
            nodes=nodes,
            metadata={
                "source_hash": source_hash,
                "cached_at": datetime.now().isoformat(),
                "total_nodes": len(nodes),
                "max_depth": max_depth,
            },
        )


def get_cache_dir(ontologies_dir: Path) -> Path:
    """Get cache directory path."""
    return ontologies_dir / ".cache"
