"""Ontology validation utilities."""

from dataclasses import dataclass, field
from pathlib import Path

import owlready2


@dataclass
class ValidationResult:
    """Result of ontology validation.

    Attributes:
        valid: Whether the ontology is valid.
        errors: List of error messages.
        warnings: List of warning messages.
        class_count: Number of classes found.
        has_root: Whether a root node exists.
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    class_count: int = 0
    has_root: bool = False


def validate_ontology(file_path: Path | str) -> ValidationResult:
    """Validate an ontology file.

    Checks:
    - File exists and is readable
    - Valid RDF/OWL format
    - Has class definitions
    - Has proper structure

    Args:
        file_path: Path to the ontology file.

    Returns:
        ValidationResult with validation status and details.
    """
    result = ValidationResult()
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        result.valid = False
        result.errors.append(f"File not found: {path}")
        return result

    # Check file extension
    if path.suffix.lower() not in {".rdf", ".owl", ".xml"}:
        result.warnings.append(
            f"Unexpected file extension: {path.suffix}. Expected .rdf, .owl, or .xml"
        )

    # Try to load the ontology
    try:
        onto = owlready2.get_ontology(str(path)).load()
    except Exception as e:
        result.valid = False
        result.errors.append(f"Failed to parse ontology: {e}")
        return result

    # Check for classes
    classes = list(onto.classes())
    result.class_count = len(classes)

    if result.class_count == 0:
        result.warnings.append("Ontology has no class definitions")

    # Check for root classes (direct subclasses of Thing)
    root_classes = []
    for cls in classes:
        parents = [p for p in cls.is_a if hasattr(p, "iri")]
        # If only parent is Thing or no explicit parents, it's a root class
        if not parents or all("Thing" in str(p) for p in parents):
            root_classes.append(cls)

    result.has_root = len(root_classes) > 0

    if not result.has_root and result.class_count > 0:
        result.warnings.append("No root classes found (classes with no parent)")

    # Check for orphan classes (classes with non-existent parents)
    class_iris = {cls.iri for cls in classes}
    for cls in classes:
        for parent in cls.is_a:
            if (
                hasattr(parent, "iri")
                and "Thing" not in parent.iri
                and parent.iri not in class_iris
            ):
                result.warnings.append(
                    f"Class {cls.name} has parent {parent.name} not in ontology"
                )

    return result


def validate_ontology_file(file_path: Path | str) -> tuple[bool, str]:
    """Simple validation that returns boolean and message.

    Args:
        file_path: Path to the ontology file.

    Returns:
        Tuple of (is_valid, message).
    """
    result = validate_ontology(file_path)

    if not result.valid:
        return False, "; ".join(result.errors)

    if result.class_count == 0:
        return False, "Ontology has no class definitions"

    message = f"Valid ontology with {result.class_count} classes"
    if result.warnings:
        message += f" (warnings: {len(result.warnings)})"

    return True, message
