"""Labels registry for managing ground truth label files."""

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class LabelsEntry:
    """Metadata for a registered labels file."""

    id: str
    filename: str
    name: str = ""
    description: str = ""
    total_tables: int = 0
    total_columns: int = 0
    file_hash: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LabelsEntry":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class LabelsRegistry:
    """Registry for managing ground truth label files."""

    labels: dict[str, LabelsEntry] = field(default_factory=dict)
    _registry_path: Path | None = field(default=None, repr=False)
    _labels_dir: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, labels_dir: Path) -> "LabelsRegistry":
        """Load registry from JSON file or create new one."""
        registry_path = labels_dir / "registry.json"
        registry = cls(_registry_path=registry_path, _labels_dir=labels_dir)

        if registry_path.exists():
            try:
                with open(registry_path, encoding="utf-8") as f:
                    data = json.load(f)
                for entry_data in data.get("labels", []):
                    entry = LabelsEntry.from_dict(entry_data)
                    registry.labels[entry.id] = entry
                logger.debug(f"Loaded labels registry with {len(registry.labels)} entries")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load labels registry: {e}, creating new one")

        return registry

    def save(self) -> None:
        """Save registry to JSON file."""
        if self._registry_path is None:
            raise ValueError("Registry path not set")

        data = {"labels": [entry.to_dict() for entry in self.labels.values()]}

        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved labels registry with {len(self.labels)} entries")

    def generate_id(self) -> str:
        """Generate a short unique ID for the labels file."""
        short_id = uuid.uuid4().hex[:8]
        while short_id in self.labels:
            short_id = uuid.uuid4().hex[:8]
        return short_id

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()[:16]}"

    def _compute_stats(self, file_path: Path) -> tuple[int, int]:
        """Compute stats from labels file.

        Returns:
            Tuple of (total_tables, total_columns)
        """
        try:
            df = pd.read_csv(file_path)
            total_tables = df["table_id"].nunique()
            total_columns = len(df)
            return total_tables, total_columns
        except Exception as e:
            logger.warning(f"Failed to compute stats for {file_path}: {e}")
            return 0, 0

    def register(
        self,
        filename: str,
        name: str = "",
        description: str = "",
        custom_id: str | None = None,
    ) -> LabelsEntry:
        """Register a new labels file.

        Args:
            filename: Labels filename
            name: Display name
            description: Description
            custom_id: Optional custom ID

        Returns:
            The created LabelsEntry
        """
        if self._labels_dir is None:
            raise ValueError("Labels directory not set")

        file_path = self._labels_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Labels file not found: {filename}")

        # Generate or use custom ID
        id_ = custom_id if custom_id else self.generate_id()

        # Compute file hash and stats
        file_hash = self.compute_file_hash(file_path)
        total_tables, total_columns = self._compute_stats(file_path)

        # Use filename as name if not provided
        if not name:
            name = filename.replace(".csv", "").replace("_", " ").title()

        entry = LabelsEntry(
            id=id_,
            filename=filename,
            name=name,
            description=description,
            total_tables=total_tables,
            total_columns=total_columns,
            file_hash=file_hash,
            created_at=datetime.now().isoformat(),
        )

        self.labels[id_] = entry
        self.save()

        logger.info(f"Registered labels: {id_} -> {filename}")
        return entry

    def unregister(self, id_: str) -> bool:
        """Unregister a labels file.

        Args:
            id_: Labels ID

        Returns:
            True if removed, False if not found
        """
        if id_ in self.labels:
            del self.labels[id_]
            self.save()
            logger.info(f"Unregistered labels: {id_}")
            return True
        return False

    def get(self, id_: str) -> LabelsEntry | None:
        """Get labels entry by ID."""
        return self.labels.get(id_)

    def get_by_filename(self, filename: str) -> LabelsEntry | None:
        """Get labels entry by filename."""
        for entry in self.labels.values():
            if entry.filename == filename:
                return entry
        return None

    def list_all(self) -> list[LabelsEntry]:
        """List all registered labels."""
        return list(self.labels.values())

    def get_file_path(self, id_or_filename: str) -> Path | None:
        """Get the file path for a labels entry.

        Args:
            id_or_filename: Labels ID or filename

        Returns:
            Path to the labels file or None if not found
        """
        if self._labels_dir is None:
            return None

        # Try by ID first
        entry = self.get(id_or_filename)
        if entry:
            return self._labels_dir / entry.filename

        # Try by filename
        entry = self.get_by_filename(id_or_filename)
        if entry:
            return self._labels_dir / entry.filename

        # Try as direct filename
        file_path = self._labels_dir / id_or_filename
        if file_path.exists():
            return file_path

        return None

    def sync_with_directory(self) -> dict[str, list[str]]:
        """Sync registry with actual files in directory.

        Returns:
            Dict with 'added', 'removed' lists
        """
        if self._labels_dir is None:
            raise ValueError("Labels directory not set")

        result = {"added": [], "removed": []}

        # Get all CSV files (excluding registry.json)
        existing_files = {
            f.name for f in self._labels_dir.glob("*.csv")
        }

        # Check for removed files
        registered_files = {e.filename for e in self.labels.values()}
        for filename in registered_files - existing_files:
            entry = self.get_by_filename(filename)
            if entry:
                self.unregister(entry.id)
                result["removed"].append(entry.id)

        # Check for new files
        for filename in existing_files - registered_files:
            entry = self.register(filename)
            result["added"].append(entry.id)

        return result
