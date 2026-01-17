"""Tests for the OntologyDAG class."""

from pathlib import Path

import pytest

from saed.ontology.dag import OntologyDAG


class TestOntologyDAG:
    """Test cases for OntologyDAG."""

    def test_init_with_path_string(self, test_ontology_path: Path):
        """Test initializing DAG with a path string."""
        dag = OntologyDAG(str(test_ontology_path))
        assert dag.rdf_file_path == str(test_ontology_path)
        assert dag.nodes == {}
        assert dag.root is None

    def test_init_with_path_object(self, test_ontology_path: Path):
        """Test initializing DAG with a Path object."""
        dag = OntologyDAG(test_ontology_path)
        assert dag.rdf_file_path == str(test_ontology_path)

    def test_init_without_path(self):
        """Test initializing DAG without a path."""
        dag = OntologyDAG()
        assert dag.rdf_file_path is None
        assert dag.nodes == {}
        assert dag.root is None

    def test_build_dag_populates_nodes(self, test_ontology_path: Path):
        """Test that build_dag populates the nodes dictionary."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        # Should have 9 classes: Energy, Measurement, Device + 6 subclasses
        assert len(dag.nodes) == 9

        # Check specific nodes exist
        node_names = {node.name for node in dag.nodes.values()}
        expected_names = {
            "Energy",
            "ElectricalEnergy",
            "ThermalEnergy",
            "Measurement",
            "Power",
            "Temperature",
            "Device",
            "Sensor",
            "Meter",
        }
        assert node_names == expected_names

    def test_build_dag_sets_root(self, test_ontology_path: Path):
        """Test that build_dag sets the root to owl:Thing."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        assert dag.root is not None
        assert "Thing" in dag.root

    def test_build_dag_creates_edges(self, test_ontology_path: Path):
        """Test that build_dag creates correct edge relationships."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        # Find Energy node URL
        energy_url = None
        for url, node in dag.nodes.items():
            if node.name == "Energy":
                energy_url = url
                break

        assert energy_url is not None

        # Energy should have ElectricalEnergy and ThermalEnergy as children
        children = dag.get_children(energy_url)
        assert len(children) == 2

        children_names = {dag.nodes[url].name for url in children}
        assert children_names == {"ElectricalEnergy", "ThermalEnergy"}

    def test_get_children_empty_for_leaf(self, test_ontology_path: Path):
        """Test that get_children returns empty list for leaf nodes."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        # Find a leaf node (ElectricalEnergy)
        leaf_url = None
        for url, node in dag.nodes.items():
            if node.name == "ElectricalEnergy":
                leaf_url = url
                break

        children = dag.get_children(leaf_url)
        assert children == []

    def test_get_children_nonexistent_url(self, test_ontology_path: Path):
        """Test get_children with a URL that doesn't exist."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        children = dag.get_children("http://nonexistent.org/class")
        assert children == []

    def test_to_dict_structure(self, test_ontology_path: Path):
        """Test that to_dict returns correct structure."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        result = dag.to_dict()

        assert "root" in result
        assert "nodes" in result
        assert "edges" in result

        assert result["root"] is not None
        assert len(result["nodes"]) == 9

    def test_to_dict_node_structure(self, test_ontology_path: Path):
        """Test that to_dict returns correct node structure."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        result = dag.to_dict()

        # Check one node structure
        for url, node_dict in result["nodes"].items():
            assert "url" in node_dict
            assert "name" in node_dict
            assert "label" in node_dict
            assert "comment" in node_dict
            assert "children" in node_dict
            break

    def test_repr(self, test_ontology_path: Path):
        """Test the string representation of OntologyDAG."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        repr_str = repr(dag)
        assert "OntologyDAG" in repr_str
        assert "nodes=" in repr_str
        assert "edges=" in repr_str

    def test_build_dag_with_explicit_path(self, test_ontology_path: Path):
        """Test build_dag with path passed directly to method."""
        dag = OntologyDAG()
        dag.build_dag(str(test_ontology_path))

        assert len(dag.nodes) == 9
        assert dag.root is not None

    def test_invalid_file_path(self, tmp_path: Path):
        """Test that build_dag raises error for invalid file."""
        dag = OntologyDAG(tmp_path / "nonexistent.rdf")

        with pytest.raises(Exception):
            dag.build_dag()

    def test_node_has_correct_attributes(self, test_ontology_path: Path):
        """Test that nodes have correct attributes from RDF."""
        dag = OntologyDAG(test_ontology_path)
        dag.build_dag()

        # Find Energy node
        energy_node = None
        for node in dag.nodes.values():
            if node.name == "Energy":
                energy_node = node
                break

        assert energy_node is not None
        assert energy_node.url is not None
        assert energy_node.name == "Energy"
        # Note: label and comment may be lists from owlready2
        # This is a known issue to be fixed in Phase B
