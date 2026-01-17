"""Tests for the OntologyClass dataclass."""

import pytest

from saed.ontology.classes import OntologyClass


class TestOntologyClass:
    """Test cases for OntologyClass."""

    def test_creation_with_url_only(self):
        """Test creating an OntologyClass with only URL."""
        cls = OntologyClass(url="http://example.org/Thing")
        assert cls.url == "http://example.org/Thing"
        assert cls.name is None
        assert cls.label is None
        assert cls.comment is None

    def test_creation_with_all_fields(self):
        """Test creating an OntologyClass with all fields."""
        cls = OntologyClass(
            url="http://example.org/Energy",
            name="Energy",
            label="Energy Label",
            comment="Represents energy concepts",
        )
        assert cls.url == "http://example.org/Energy"
        assert cls.name == "Energy"
        assert cls.label == "Energy Label"
        assert cls.comment == "Represents energy concepts"

    def test_creation_with_partial_fields(self):
        """Test creating an OntologyClass with some optional fields."""
        cls = OntologyClass(
            url="http://example.org/Measurement",
            name="Measurement",
        )
        assert cls.url == "http://example.org/Measurement"
        assert cls.name == "Measurement"
        assert cls.label is None
        assert cls.comment is None

    def test_repr(self):
        """Test the string representation of OntologyClass."""
        cls = OntologyClass(
            url="http://example.org/Device",
            name="Device",
            label="Device Label",
            comment="A device",
        )
        repr_str = repr(cls)
        assert "OntologyClass" in repr_str
        assert "url='http://example.org/Device'" in repr_str
        assert "name='Device'" in repr_str
        assert "label='Device Label'" in repr_str
        assert "comment='A device'" in repr_str

    def test_repr_with_none_values(self):
        """Test repr when optional fields are None."""
        cls = OntologyClass(url="http://example.org/Thing")
        repr_str = repr(cls)
        assert "name='None'" in repr_str
        assert "label='None'" in repr_str
        assert "comment='None'" in repr_str

    def test_equality(self):
        """Test that two OntologyClass instances with same values are equal."""
        cls1 = OntologyClass(url="http://example.org/Energy", name="Energy")
        cls2 = OntologyClass(url="http://example.org/Energy", name="Energy")
        assert cls1 == cls2

    def test_inequality(self):
        """Test that two OntologyClass instances with different values are not equal."""
        cls1 = OntologyClass(url="http://example.org/Energy", name="Energy")
        cls2 = OntologyClass(url="http://example.org/Power", name="Power")
        assert cls1 != cls2

    def test_url_is_required(self):
        """Test that url is a required field."""
        with pytest.raises(TypeError):
            OntologyClass()  # type: ignore
