"""Ontology registry for managing ID-file mappings and metadata."""

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OntologyEntry:
    """Metadata for a registered ontology."""

    id: str
    filename: str
    class_count: int = 0
    max_depth: int = 0
    file_hash: str = ""
    cached_at: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OntologyEntry":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class OntologyRegistry:
    """Registry for managing ontologies."""

    ontologies: dict[str, OntologyEntry] = field(default_factory=dict)
    _registry_path: Path | None = field(default=None, repr=False)
    _ontologies_dir: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, ontologies_dir: Path) -> "OntologyRegistry":
        """Load registry from JSON file or create new one."""
        registry_path = ontologies_dir / "registry.json"
        registry = cls(_registry_path=registry_path, _ontologies_dir=ontologies_dir)

        if registry_path.exists():
            try:
                with open(registry_path, encoding="utf-8") as f:
                    data = json.load(f)
                for id_, entry_data in data.get("ontologies", {}).items():
                    registry.ontologies[id_] = OntologyEntry.from_dict(entry_data)
                logger.debug(f"Loaded registry with {len(registry.ontologies)} entries")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load registry: {e}, creating new one")

        return registry

    def save(self) -> None:
        """Save registry to JSON file."""
        if self._registry_path is None:
            raise ValueError("Registry path not set")

        data = {
            "ontologies": {id_: entry.to_dict() for id_, entry in self.ontologies.items()}
        }

        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved registry with {len(self.ontologies)} entries")

    def generate_id(self) -> str:
        """Generate a short unique ID for the ontology.

        Returns:
            8-character hex string (e.g., 'a1b2c3d4')
        """
        # Use first 8 chars of UUID (32-bit, ~4 billion unique values)
        short_id = uuid.uuid4().hex[:8]

        # Handle collision (very rare)
        while short_id in self.ontologies:
            short_id = uuid.uuid4().hex[:8]

        return short_id

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()[:16]}"

    def register(
        self,
        filename: str,
        class_count: int = 0,
        max_depth: int = 0,
        custom_id: str | None = None,
    ) -> OntologyEntry:
        """Register a new ontology.

        Args:
            filename: Ontology filename
            class_count: Number of classes
            max_depth: Maximum tree depth
            custom_id: Optional custom ID (otherwise auto-generated)

        Returns:
            The created OntologyEntry
        """
        if self._ontologies_dir is None:
            raise ValueError("Ontologies directory not set")

        file_path = self._ontologies_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Ontology file not found: {filename}")

        # Generate or use custom ID
        id_ = custom_id if custom_id else self.generate_id()

        # Compute file hash
        file_hash = self.compute_file_hash(file_path)

        entry = OntologyEntry(
            id=id_,
            filename=filename,
            class_count=class_count,
            max_depth=max_depth,
            file_hash=file_hash,
            cached_at=datetime.now().isoformat(),
        )

        self.ontologies[id_] = entry
        self.save()

        logger.info(f"Registered ontology: {id_} -> {filename}")
        return entry

    def unregister(self, id_: str) -> bool:
        """Unregister an ontology.

        Args:
            id_: Ontology ID

        Returns:
            True if removed, False if not found
        """
        if id_ in self.ontologies:
            del self.ontologies[id_]
            self.save()
            logger.info(f"Unregistered ontology: {id_}")
            return True
        return False

    def get(self, id_: str) -> OntologyEntry | None:
        """Get ontology entry by ID."""
        return self.ontologies.get(id_)

    def get_by_filename(self, filename: str) -> OntologyEntry | None:
        """Get ontology entry by filename."""
        for entry in self.ontologies.values():
            if entry.filename == filename:
                return entry
        return None

    def list_all(self) -> list[OntologyEntry]:
        """List all registered ontologies."""
        return list(self.ontologies.values())

    def update(
        self,
        id_: str,
        class_count: int | None = None,
        max_depth: int | None = None,
    ) -> OntologyEntry | None:
        """Update ontology metadata.

        Args:
            id_: Ontology ID
            class_count: New class count
            max_depth: New max depth

        Returns:
            Updated entry or None if not found
        """
        entry = self.ontologies.get(id_)
        if entry is None:
            return None

        if class_count is not None:
            entry.class_count = class_count
        if max_depth is not None:
            entry.max_depth = max_depth

        # Update file hash if file changed
        if self._ontologies_dir:
            file_path = self._ontologies_dir / entry.filename
            if file_path.exists():
                new_hash = self.compute_file_hash(file_path)
                if new_hash != entry.file_hash:
                    entry.file_hash = new_hash
                    entry.cached_at = datetime.now().isoformat()

        self.save()
        return entry

    def is_cache_valid(self, id_: str) -> bool:
        """Check if cached data is still valid based on file hash.

        Args:
            id_: Ontology ID

        Returns:
            True if cache is valid, False if file changed or not found
        """
        entry = self.ontologies.get(id_)
        if entry is None or not self._ontologies_dir:
            return False

        file_path = self._ontologies_dir / entry.filename
        if not file_path.exists():
            return False

        current_hash = self.compute_file_hash(file_path)
        return current_hash == entry.file_hash

    def sync_with_directory(self) -> dict[str, list[str]]:
        """Sync registry with actual files in directory.

        Returns:
            Dict with 'added', 'removed', and 'updated' lists
        """
        if self._ontologies_dir is None:
            raise ValueError("Ontologies directory not set")

        result = {"added": [], "removed": [], "updated": []}

        # Get all ontology files
        existing_files = set()
        for ext in ("*.rdf", "*.owl"):
            for file in self._ontologies_dir.glob(ext):
                existing_files.add(file.name)

        # Check for removed files
        registered_files = {e.filename for e in self.ontologies.values()}
        for filename in registered_files - existing_files:
            entry = self.get_by_filename(filename)
            if entry:
                self.unregister(entry.id)
                result["removed"].append(entry.id)

        # Check for new files
        for filename in existing_files - registered_files:
            entry = self.register(filename)
            result["added"].append(entry.id)

        # Check for updated files (hash changed)
        for entry in list(self.ontologies.values()):
            if not self.is_cache_valid(entry.id):
                result["updated"].append(entry.id)

        return result
