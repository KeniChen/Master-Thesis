"""Ontology DAG (Directed Acyclic Graph) representation."""

from collections import defaultdict
from pathlib import Path
from typing import Any

import owlready2
from owlready2 import Thing

from saed.core.config.settings import get_project_root
from saed.core.ontology.classes import OntologyClass


class OntologyDAG:
    """Represents the ontology as a Directed Acyclic Graph (DAG).

    Attributes:
        nodes: A dictionary mapping URLs to OntologyClass instances.
        edges: A dictionary mapping URLs to lists of child URLs.
        root: The root node URL.
    """

    def __init__(self, config_or_path: str | Path | Any = None):
        """Initialize the OntologyDAG.

        Args:
            config_or_path: Either a file path to the RDF/OWL file,
                           or a config object with ontology path.
        """
        self.rdf_file_path: str | None = None

        if config_or_path is not None:
            if isinstance(config_or_path, (str, Path)):
                # Direct file path
                self.rdf_file_path = str(config_or_path)
            elif hasattr(config_or_path, "__getitem__"):
                # Config-like object (DictConfig or dict)
                try:
                    root_path = get_project_root()
                    self.rdf_file_path = str(root_path / config_or_path["data"]["ontology"]["path"])
                except (KeyError, TypeError):
                    pass

        self.nodes: dict[str, OntologyClass] = {}
        self.edges_subclassof: dict[str, list[str]] = defaultdict(list)
        self.edges: dict[str, list[str]] = defaultdict(list)
        self.root: str | None = None

    def build_dag(self, rdf_file_path: str | None = None) -> None:
        """Build the ontology DAG from an RDF file.

        Args:
            rdf_file_path: Optional path to the RDF file. If not provided,
                          uses the path from config.
        """
        if rdf_file_path is not None:
            self.rdf_file_path = rdf_file_path

        onto = owlready2.get_ontology(self.rdf_file_path).load()

        for cls in onto.classes():
            url = cls.iri
            # Extract first label/comment (owlready2 returns IndividualValueList)
            # Use len() explicitly as IndividualValueList may have different truthiness
            # Convert to str to handle localized strings (e.g., locstr objects)
            raw_label = cls.label[0] if len(cls.label) > 0 else None
            raw_comment = cls.comment[0] if len(cls.comment) > 0 else None
            label = str(raw_label) if raw_label is not None else None
            comment = str(raw_comment) if raw_comment is not None else None
            self.nodes[url] = OntologyClass(
                url=url,
                name=cls.name,
                label=label,
                comment=comment,
            )
            # Get parent classes (superclasses) and add this class as their child
            for parent in cls.is_a:
                # Skip Thing and non-class parents (like restrictions)
                if not hasattr(parent, "iri"):
                    continue
                parent_url = parent.iri
                if parent_url == url:
                    continue
                if parent_url not in self.edges_subclassof:
                    self.edges_subclassof[parent_url] = []
                self.edges_subclassof[parent_url].append(url)

        # Build reverse edges (child -> parents)
        self.edges = {k: [] for k in self.nodes}
        for parent, children in self.edges_subclassof.items():
            for child in children:
                if child in self.edges:
                    self.edges[child].append(parent)

        # Find classes without parents (root candidates)
        all_children = set()
        for children in self.edges_subclassof.values():
            all_children.update(children)

        root_candidates = [url for url in self.nodes if url not in all_children]

        if len(root_candidates) == 1:
            # Single root class
            self.root = root_candidates[0]
        elif len(root_candidates) > 1:
            # Multiple roots - use owl:Thing as virtual root
            self.root = Thing.iri
            # Add root candidates as children of Thing
            self.edges_subclassof[self.root] = root_candidates
            # Add virtual Thing node
            self.nodes[self.root] = OntologyClass(
                url=self.root,
                name="Thing",
                label="Thing",
                comment="Root class (owl:Thing)",
            )
        else:
            # No root candidates - owl:Thing is the root
            self.root = Thing.iri
            # Add virtual Thing node if not present
            if self.root not in self.nodes:
                self.nodes[self.root] = OntologyClass(
                    url=self.root,
                    name="Thing",
                    label="Thing",
                    comment="Root class (owl:Thing)",
                )

    def __repr__(self) -> str:
        return f"OntologyDAG(nodes={list(self.nodes.keys())}, edges={dict(self.edges)})"

    def to_dict(self) -> dict:
        """Convert the DAG to a dictionary representation.

        Returns:
            A dictionary with root, nodes, and edges.
        """
        nodes_dict = {}
        for url, ontology_class in self.nodes.items():
            nodes_dict[url] = {
                "url": ontology_class.url,
                "name": ontology_class.name,
                "label": ontology_class.label,
                "comment": ontology_class.comment,
                "children": self.edges_subclassof.get(url, []),
            }

        return {
            "root": self.root,
            "nodes": nodes_dict,
            "edges": dict(self.edges_subclassof),
        }

    def get_children(self, url: str) -> list[str]:
        """Get the children of a node.

        Args:
            url: The URL of the parent node.

        Returns:
            A list of child URLs.
        """
        return self.edges_subclassof.get(url, [])
