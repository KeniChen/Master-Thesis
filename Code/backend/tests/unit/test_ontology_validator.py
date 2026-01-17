"""Tests for the ontology validator."""

from pathlib import Path

import pytest

from saed.ontology.validator import ValidationResult, validate_ontology, validate_ontology_file


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self):
        """Test default values are correct."""
        result = ValidationResult()
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.class_count == 0
        assert result.has_root is False

    def test_custom_values(self):
        """Test custom values."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1"],
            warnings=["Warning 1"],
            class_count=10,
            has_root=True,
        )
        assert result.valid is False
        assert result.errors == ["Error 1"]
        assert result.class_count == 10


class TestValidateOntology:
    """Tests for validate_ontology function."""

    def test_valid_ontology(self, test_ontology_path: Path):
        """Test validating a valid ontology."""
        result = validate_ontology(test_ontology_path)

        assert result.valid is True
        assert result.errors == []
        assert result.class_count == 9
        assert result.has_root is True

    def test_nonexistent_file(self, tmp_path: Path):
        """Test validating a nonexistent file."""
        result = validate_ontology(tmp_path / "nonexistent.rdf")

        assert result.valid is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()

    def test_invalid_format(self, tmp_path: Path):
        """Test validating an invalid RDF file."""
        invalid_file = tmp_path / "invalid.rdf"
        invalid_file.write_text("This is not valid RDF")

        result = validate_ontology(invalid_file)

        assert result.valid is False
        assert len(result.errors) > 0

    def test_empty_ontology(self, tmp_path: Path):
        """Test validating an ontology with no classes."""
        empty_ontology = tmp_path / "empty.rdf"
        empty_ontology.write_text("""<?xml version="1.0"?>
<rdf:RDF xmlns="http://example.org/empty#"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    <owl:Ontology rdf:about="http://example.org/empty"/>
</rdf:RDF>
""")

        result = validate_ontology(empty_ontology)

        assert result.valid is True  # Valid format, just empty
        assert result.class_count == 0
        assert any("no class" in w.lower() for w in result.warnings)

    def test_unexpected_extension_warning(self, tmp_path: Path, test_ontology_path: Path):
        """Test warning for unexpected file extension."""
        # Copy valid ontology with different extension
        weird_file = tmp_path / "ontology.txt"
        weird_file.write_text(test_ontology_path.read_text())

        result = validate_ontology(weird_file)

        # Should still be valid but with warning
        assert result.valid is True
        assert any("extension" in w.lower() for w in result.warnings)


class TestValidateOntologyFile:
    """Tests for validate_ontology_file function."""

    def test_valid_ontology(self, test_ontology_path: Path):
        """Test simple validation of valid ontology."""
        is_valid, message = validate_ontology_file(test_ontology_path)

        assert is_valid is True
        assert "9 classes" in message

    def test_invalid_file(self, tmp_path: Path):
        """Test simple validation of invalid file."""
        invalid_file = tmp_path / "invalid.rdf"
        invalid_file.write_text("not valid")

        is_valid, message = validate_ontology_file(invalid_file)

        assert is_valid is False
        assert len(message) > 0

    def test_empty_ontology(self, tmp_path: Path):
        """Test simple validation of empty ontology."""
        empty_ontology = tmp_path / "empty.rdf"
        empty_ontology.write_text("""<?xml version="1.0"?>
<rdf:RDF xmlns="http://example.org/empty#"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <owl:Ontology rdf:about="http://example.org/empty"/>
</rdf:RDF>
""")

        is_valid, message = validate_ontology_file(empty_ontology)

        assert is_valid is False
        assert "no class" in message.lower()
