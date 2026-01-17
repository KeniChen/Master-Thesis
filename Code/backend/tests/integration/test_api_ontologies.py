"""Integration tests for the ontologies API endpoints."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from saed.api.main import app


@pytest.fixture
def api_client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_ontologies_dir(tmp_path: Path, fixtures_dir: Path):
    """Create a mock ontologies directory with test ontology."""
    ontologies_dir = tmp_path / "ontologies"
    ontologies_dir.mkdir()

    # Create cache directory
    cache_dir = ontologies_dir / ".cache"
    cache_dir.mkdir()

    # Copy test ontology to mock directory
    test_ontology = fixtures_dir / "test_ontology.rdf"
    if test_ontology.exists():
        shutil.copy(test_ontology, ontologies_dir / "test_ontology.rdf")

    return ontologies_dir


@pytest.fixture
def patched_ontologies_dir(mock_ontologies_dir: Path):
    """Patch the get_ontologies_dir function to use mock directory."""
    with patch(
        "saed.api.routes.ontologies.get_ontologies_dir",
        return_value=mock_ontologies_dir,
    ):
        yield mock_ontologies_dir


def get_test_ontology_id(api_client: TestClient) -> str:
    """Helper to get the registered ID for test_ontology."""
    response = api_client.get("/api/ontologies")
    if response.status_code == 200:
        ontologies = response.json().get("ontologies", [])
        for onto in ontologies:
            if onto.get("filename") == "test_ontology.rdf" or onto.get("name") == "test_ontology":
                return onto["id"]
    # Fallback to slug format
    return "test-ontology"


class TestListOntologies:
    """Tests for GET /api/ontologies endpoint."""

    def test_list_ontologies_empty(self, api_client: TestClient, tmp_path: Path):
        """Test listing ontologies when directory is empty."""
        empty_dir = tmp_path / "empty_ontologies"
        empty_dir.mkdir()
        # Create cache dir
        (empty_dir / ".cache").mkdir()

        with patch(
            "saed.api.routes.ontologies.get_ontologies_dir",
            return_value=empty_dir,
        ):
            response = api_client.get("/api/ontologies")

        assert response.status_code == 200
        data = response.json()
        assert "ontologies" in data
        assert data["ontologies"] == []

    def test_list_ontologies_with_files(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test listing ontologies when files exist."""
        response = api_client.get("/api/ontologies")

        assert response.status_code == 200
        data = response.json()
        assert "ontologies" in data
        assert len(data["ontologies"]) >= 1

        # Check structure of returned ontology
        ontology = data["ontologies"][0]
        assert "id" in ontology
        assert "name" in ontology
        assert "class_count" in ontology
        assert "filename" in ontology


class TestGetOntologyTree:
    """Tests for GET /api/ontologies/{id}/tree endpoint."""

    def test_get_tree_success(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting ontology tree structure."""
        # First list to register the ontology
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.get(f"/api/ontologies/{ontology_id}/tree")

        assert response.status_code == 200
        data = response.json()
        assert "root" in data
        assert "nodes" in data
        assert "total_nodes" in data

    def test_get_tree_with_depth_limit(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting ontology tree with depth limit."""
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.get(f"/api/ontologies/{ontology_id}/tree?depth=1")

        assert response.status_code == 200
        data = response.json()
        assert "root" in data
        assert "nodes" in data
        # With depth=1, should have fewer nodes or truncated flag
        assert "truncated" in data

    def test_get_tree_not_found(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting tree for non-existent ontology."""
        response = api_client.get("/api/ontologies/nonexistent/tree")

        assert response.status_code == 404


class TestGetOntologyClasses:
    """Tests for GET /api/ontologies/{id}/classes endpoint."""

    def test_get_classes_success(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting ontology classes."""
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.get(f"/api/ontologies/{ontology_id}/classes")

        assert response.status_code == 200
        data = response.json()
        assert "classes" in data
        assert "total" in data

    def test_get_classes_with_search(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test searching ontology classes."""
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.get(
            f"/api/ontologies/{ontology_id}/classes",
            params={"search": "Energy"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should find Energy-related classes
        assert data["total"] > 0

    def test_get_classes_not_found(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting classes for non-existent ontology."""
        response = api_client.get("/api/ontologies/nonexistent/classes")

        assert response.status_code == 404


class TestUploadOntology:
    """Tests for POST /api/ontologies endpoint."""

    def test_upload_ontology_success(
        self, api_client: TestClient, patched_ontologies_dir: Path, fixtures_dir: Path
    ):
        """Test uploading a valid ontology file."""
        test_ontology = fixtures_dir / "test_ontology.rdf"

        with open(test_ontology, "rb") as f:
            response = api_client.post(
                "/api/ontologies",
                files={"file": ("uploaded.rdf", f, "application/rdf+xml")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        # ID is now an 8-character hex UUID
        assert len(data["id"]) == 8
        assert all(c in "0123456789abcdef" for c in data["id"])
        assert data["filename"] == "uploaded.rdf"

    def test_upload_ontology_invalid_extension(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test uploading a file with invalid extension."""
        response = api_client.post(
            "/api/ontologies",
            files={"file": ("test.txt", b"not an ontology", "text/plain")},
        )

        assert response.status_code == 400
        assert "RDF/OWL" in response.json()["detail"]


class TestDeleteOntology:
    """Tests for DELETE /api/ontologies/{id} endpoint."""

    def test_delete_ontology_success(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test deleting an existing ontology."""
        # First verify the file exists
        assert (patched_ontologies_dir / "test_ontology.rdf").exists()

        # Get the registered ID
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.delete(f"/api/ontologies/{ontology_id}")

        assert response.status_code == 200
        assert not (patched_ontologies_dir / "test_ontology.rdf").exists()

    def test_delete_ontology_not_found(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test deleting a non-existent ontology."""
        response = api_client.delete("/api/ontologies/nonexistent")

        assert response.status_code == 404


class TestGetOntologyInfo:
    """Tests for GET /api/ontologies/{id} endpoint."""

    def test_get_ontology_info_success(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting ontology information."""
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.get(f"/api/ontologies/{ontology_id}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "class_count" in data
        assert data["class_count"] == 9  # Our test ontology has 9 classes

    def test_get_ontology_info_not_found(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test getting info for non-existent ontology."""
        response = api_client.get("/api/ontologies/nonexistent")

        assert response.status_code == 404


class TestValidateOntology:
    """Tests for GET /api/ontologies/{id}/validate endpoint."""

    def test_validate_ontology_success(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test validating a valid ontology."""
        ontology_id = get_test_ontology_id(api_client)

        response = api_client.get(f"/api/ontologies/{ontology_id}/validate")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["valid"] is True
        assert data["class_count"] == 9
        assert data["has_root"] is True
        assert data["errors"] == []

    def test_validate_ontology_not_found(
        self, api_client: TestClient, patched_ontologies_dir: Path
    ):
        """Test validating a non-existent ontology."""
        response = api_client.get("/api/ontologies/nonexistent/validate")

        assert response.status_code == 404
