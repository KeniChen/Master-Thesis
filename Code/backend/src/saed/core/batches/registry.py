"""Batch registry for managing experiment batch result files."""

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration info extracted from a batch file."""

    ontology_id: str = ""
    mode: str = ""
    prompt_type: str = ""
    max_depth: int = 0
    k: int = 0
    provider: str = ""
    model: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BatchConfig":
        """Create from dictionary."""
        return cls(
            ontology_id=data.get("ontology_id", ""),
            mode=data.get("mode", ""),
            prompt_type=data.get("prompt_type", ""),
            max_depth=data.get("max_depth", 0),
            k=data.get("k", 0),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
        )


@dataclass
class BatchEntry:
    """Metadata for a registered batch file."""

    id: str
    filename: str
    name: str = ""
    description: str = ""
    run_id: str = ""
    total_tables: int = 0
    total_columns: int = 0
    completed_columns: int = 0
    config: BatchConfig = field(default_factory=BatchConfig)
    file_hash: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["config"] = self.config.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "BatchEntry":
        """Create from dictionary."""
        config_data = data.pop("config", {})
        config = BatchConfig.from_dict(config_data) if config_data else BatchConfig()
        return cls(config=config, **data)


@dataclass
class BatchRegistry:
    """Registry for managing experiment batch result files."""

    batches: dict[str, BatchEntry] = field(default_factory=dict)
    _registry_path: Path | None = field(default=None, repr=False)
    _batches_dir: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, batches_dir: Path) -> "BatchRegistry":
        """Load registry from JSON file or create new one."""
        registry_path = batches_dir / "registry.json"
        registry = cls(_registry_path=registry_path, _batches_dir=batches_dir)

        if registry_path.exists():
            try:
                with open(registry_path, encoding="utf-8") as f:
                    data = json.load(f)
                for entry_data in data.get("batches", []):
                    entry = BatchEntry.from_dict(entry_data)
                    registry.batches[entry.id] = entry
                logger.debug(f"Loaded batch registry with {len(registry.batches)} entries")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load batch registry: {e}, creating new one")

        return registry

    def save(self) -> None:
        """Save registry to JSON file."""
        if self._registry_path is None:
            raise ValueError("Registry path not set")

        data = {"batches": [entry.to_dict() for entry in self.batches.values()]}

        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved batch registry with {len(self.batches)} entries")

    def generate_id(self) -> str:
        """Generate a short unique ID for the batch file."""
        short_id = uuid.uuid4().hex[:8]
        while short_id in self.batches:
            short_id = uuid.uuid4().hex[:8]
        return short_id

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()[:16]}"

    def _extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from batch JSON file.

        Returns:
            Dict with run_id, config, total_tables, total_columns, completed_columns
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            run_id = data.get("run_id", "")
            config_data = data.get("config", {})
            summary = data.get("summary", {})

            return {
                "run_id": run_id,
                "config": BatchConfig.from_dict(config_data),
                "total_tables": summary.get("total_tables", 0),
                "total_columns": summary.get("total_columns", 0),
                "completed_columns": summary.get("completed_columns", 0),
                "created_at": data.get("created_at", ""),
            }
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            return {
                "run_id": "",
                "config": BatchConfig(),
                "total_tables": 0,
                "total_columns": 0,
                "completed_columns": 0,
                "created_at": "",
            }

    def register(
        self,
        filename: str,
        name: str = "",
        description: str = "",
        custom_id: str | None = None,
    ) -> BatchEntry:
        """Register a new batch file.

        Args:
            filename: Batch filename
            name: Display name
            description: Description
            custom_id: Optional custom ID

        Returns:
            The created BatchEntry
        """
        if self._batches_dir is None:
            raise ValueError("Batches directory not set")

        file_path = self._batches_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Batch file not found: {filename}")

        # Generate or use custom ID
        id_ = custom_id if custom_id else self.generate_id()

        # Compute file hash and extract metadata
        file_hash = self.compute_file_hash(file_path)
        metadata = self._extract_metadata(file_path)

        # Generate name from config if not provided
        if not name:
            config = metadata["config"]
            parts = []
            if config.mode:
                parts.append(config.mode)
            if config.prompt_type:
                parts.append(config.prompt_type)
            if config.ontology_id:
                parts.append(config.ontology_id.replace(".rdf", ""))
            name = " | ".join(parts) if parts else filename.replace(".json", "")

        # Use file's created_at or current time
        created_at = metadata["created_at"] or datetime.now().isoformat()

        entry = BatchEntry(
            id=id_,
            filename=filename,
            name=name,
            description=description,
            run_id=metadata["run_id"],
            total_tables=metadata["total_tables"],
            total_columns=metadata["total_columns"],
            completed_columns=metadata["completed_columns"],
            config=metadata["config"],
            file_hash=file_hash,
            created_at=created_at,
        )

        self.batches[id_] = entry
        self.save()

        logger.info(f"Registered batch: {id_} -> {filename}")
        return entry

    def unregister(self, id_: str) -> bool:
        """Unregister a batch file.

        Args:
            id_: Batch ID

        Returns:
            True if removed, False if not found
        """
        if id_ in self.batches:
            del self.batches[id_]
            self.save()
            logger.info(f"Unregistered batch: {id_}")
            return True
        return False

    def get(self, id_: str) -> BatchEntry | None:
        """Get batch entry by ID."""
        return self.batches.get(id_)

    def get_by_filename(self, filename: str) -> BatchEntry | None:
        """Get batch entry by filename."""
        for entry in self.batches.values():
            if entry.filename == filename:
                return entry
        return None

    def list_all(self) -> list[BatchEntry]:
        """List all registered batches."""
        return list(self.batches.values())

    def get_file_path(self, id_or_filename: str) -> Path | None:
        """Get the file path for a batch entry.

        Args:
            id_or_filename: Batch ID or filename

        Returns:
            Path to the batch file or None if not found
        """
        if self._batches_dir is None:
            return None

        # Try by ID first
        entry = self.get(id_or_filename)
        if entry:
            return self._batches_dir / entry.filename

        # Try by filename
        entry = self.get_by_filename(id_or_filename)
        if entry:
            return self._batches_dir / entry.filename

        # Try as direct filename
        file_path = self._batches_dir / id_or_filename
        if file_path.exists():
            return file_path

        return None

    def sync_with_directory(self) -> dict[str, list[str]]:
        """Sync registry with actual files in directory.

        Returns:
            Dict with 'added', 'removed' lists
        """
        if self._batches_dir is None:
            raise ValueError("Batches directory not set")

        result = {"added": [], "removed": []}

        # Get all JSON files (excluding registry.json)
        existing_files = {
            f.name for f in self._batches_dir.glob("*.json")
            if f.name != "registry.json"
        }

        # Check for removed files
        registered_files = {e.filename for e in self.batches.values()}
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
