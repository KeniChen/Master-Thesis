"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from saed.api.main import app


@pytest.fixture
def test_client():
    """Create a test client for API testing."""
    return TestClient(app)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_ontology_path(fixtures_dir: Path) -> Path:
    """Return the path to the test ontology file."""
    return fixtures_dir / "test_ontology.rdf"


@pytest.fixture
def temp_ontology_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for ontology tests."""
    ontology_dir = tmp_path / "ontologies"
    ontology_dir.mkdir()
    return ontology_dir
