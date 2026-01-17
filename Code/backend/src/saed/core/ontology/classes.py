"""Ontology class representation."""

from dataclasses import dataclass


@dataclass
class OntologyClass:
    """Represents a class in the ontology.

    Attributes:
        url: The unique identifier or URL for the ontology class.
        name: The name of the ontology class.
        label: The label of the ontology class.
        comment: A comment or description of the ontology class.
    """

    url: str
    name: str | None = None
    label: str | None = None
    comment: str | None = None

    def __repr__(self) -> str:
        return (
            f"OntologyClass(url='{self.url}', name='{self.name}', "
            f"label='{self.label}', comment='{self.comment}')"
        )
