"""Table registry for managing ID-file mappings and metadata."""

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
class TableEntry:
    """Metadata for a registered table."""

    id: str
    filename: str
    name: str
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    file_hash: str = ""
    category: str = "default"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TableEntry":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TableRegistry:
    """Registry for managing tables."""

    tables: dict[str, TableEntry] = field(default_factory=dict)
    _registry_path: Path | None = field(default=None, repr=False)
    _tables_dir: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, tables_dir: Path) -> "TableRegistry":
        """Load registry from JSON file or create new one."""
        registry_path = tables_dir / "registry.json"
        registry = cls(_registry_path=registry_path, _tables_dir=tables_dir)

        if registry_path.exists():
            try:
                with open(registry_path, encoding="utf-8") as f:
                    data = json.load(f)
                for id_, entry_data in data.get("tables", {}).items():
                    registry.tables[id_] = TableEntry.from_dict(entry_data)
                logger.debug(f"Loaded table registry with {len(registry.tables)} entries")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load table registry: {e}, creating new one")

        return registry

    def save(self) -> None:
        """Save registry to JSON file."""
        if self._registry_path is None:
            raise ValueError("Registry path not set")

        data = {
            "tables": {id_: entry.to_dict() for id_, entry in self.tables.items()},
            "version": "1.0",
        }

        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved table registry with {len(self.tables)} entries")

    def generate_id(self) -> str:
        """Generate a short unique ID for the table."""
        short_id = uuid.uuid4().hex[:8]
        while short_id in self.tables:
            short_id = uuid.uuid4().hex[:8]
        return short_id

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()[:16]}"

    def _extract_metadata(self, file_path: Path) -> tuple[list[str], int]:
        """Extract columns and row count from CSV file."""
        df = pd.read_csv(file_path)
        return df.columns.tolist(), len(df)

    def _get_file_path(self, filename: str, category: str) -> Path:
        """Get full file path for a table."""
        if self._tables_dir is None:
            raise ValueError("Tables directory not set")

        if category and category != "default":
            return self._tables_dir / category / filename
        return self._tables_dir / filename

    def register(
        self,
        filename: str,
        name: str | None = None,
        category: str = "default",
        custom_id: str | None = None,
    ) -> TableEntry:
        """Register a new table.

        Args:
            filename: CSV filename
            name: Human-readable name (defaults to filename stem)
            category: Subdirectory category (real, synthetic, etc.)
            custom_id: Optional custom ID

        Returns:
            The created TableEntry
        """
        file_path = self._get_file_path(filename, category)
        if not file_path.exists():
            raise FileNotFoundError(f"Table file not found: {file_path}")

        # Generate or use custom ID
        id_ = custom_id if custom_id else self.generate_id()

        # Extract metadata from CSV
        columns, row_count = self._extract_metadata(file_path)

        # Compute file hash
        file_hash = self.compute_file_hash(file_path)

        now = datetime.now().isoformat()

        entry = TableEntry(
            id=id_,
            filename=filename,
            name=name or file_path.stem,
            columns=columns,
            row_count=row_count,
            column_count=len(columns),
            file_hash=file_hash,
            category=category,
            created_at=now,
            updated_at=now,
        )

        self.tables[id_] = entry
        self.save()

        logger.info(f"Registered table: {id_} -> {filename} ({category})")
        return entry

    def unregister(self, id_: str) -> bool:
        """Unregister a table."""
        if id_ in self.tables:
            del self.tables[id_]
            self.save()
            logger.info(f"Unregistered table: {id_}")
            return True
        return False

    def get(self, id_: str) -> TableEntry | None:
        """Get table entry by ID."""
        return self.tables.get(id_)

    def get_by_filename(self, filename: str, category: str | None = None) -> TableEntry | None:
        """Get table entry by filename."""
        for entry in self.tables.values():
            if entry.filename == filename and (category is None or entry.category == category):
                return entry
        return None

    def list_all(self, category: str | None = None) -> list[TableEntry]:
        """List all registered tables, optionally filtered by category."""
        if category is None:
            return list(self.tables.values())
        return [e for e in self.tables.values() if e.category == category]

    def update(self, id_: str, **kwargs) -> TableEntry | None:
        """Update table metadata."""
        entry = self.tables.get(id_)
        if entry is None:
            return None

        for key, value in kwargs.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)

        entry.updated_at = datetime.now().isoformat()

        # Re-extract metadata if file changed
        file_path = self._get_file_path(entry.filename, entry.category)
        if file_path.exists():
            new_hash = self.compute_file_hash(file_path)
            if new_hash != entry.file_hash:
                entry.file_hash = new_hash
                columns, row_count = self._extract_metadata(file_path)
                entry.columns = columns
                entry.row_count = row_count
                entry.column_count = len(columns)

        self.save()
        return entry

    def is_cache_valid(self, id_: str) -> bool:
        """Check if cached data is still valid based on file hash."""
        entry = self.tables.get(id_)
        if entry is None:
            return False

        file_path = self._get_file_path(entry.filename, entry.category)
        if not file_path.exists():
            return False

        current_hash = self.compute_file_hash(file_path)
        return current_hash == entry.file_hash

    def _get_name_from_table_list(self, filename: str, category: str) -> str | None:
        """Try to get table name from table_list.csv."""
        if self._tables_dir is None:
            return None

        if category and category != "default":
            table_list_path = self._tables_dir / category / "table_list.csv"
        else:
            table_list_path = self._tables_dir / "table_list.csv"

        if not table_list_path.exists():
            return None

        try:
            df = pd.read_csv(table_list_path)
            row = df[df["table_id"] == filename]
            if not row.empty:
                name = row.iloc[0]["table_name"]
                # Remove .csv extension if present
                if isinstance(name, str) and name.endswith(".csv"):
                    return name[:-4].strip()
                return str(name).strip() if name else None
        except Exception as e:
            logger.warning(f"Failed to read table_list.csv: {e}")

        return None

    def sync_with_directory(self) -> dict[str, list[str]]:
        """Sync registry with actual files in directory.

        Scans both root directory and subdirectories (real, synthetic, etc.)

        Returns:
            Dict with 'added', 'removed', and 'updated' lists
        """
        if self._tables_dir is None:
            raise ValueError("Tables directory not set")

        # Ensure base directory exists to avoid runtime errors
        self._tables_dir.mkdir(parents=True, exist_ok=True)

        result = {"added": [], "removed": [], "updated": []}

        # Collect existing files with their categories
        existing_files: dict[tuple[str, str], Path] = {}  # (filename, category) -> path

        # Check root directory
        for file in self._tables_dir.glob("*.csv"):
            if file.name != "table_list.csv":
                existing_files[(file.name, "default")] = file

        # Check subdirectories
        for subdir in self._tables_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                for file in subdir.glob("*.csv"):
                    if file.name != "table_list.csv":
                        existing_files[(file.name, subdir.name)] = file

        # Build set of registered (filename, category) pairs
        registered_pairs = {(e.filename, e.category) for e in self.tables.values()}

        # Check for removed files
        for pair in registered_pairs - set(existing_files.keys()):
            filename, category = pair
            entry = self.get_by_filename(filename, category)
            if entry:
                self.unregister(entry.id)
                result["removed"].append(entry.id)

        # Check for new files
        for pair in set(existing_files.keys()) - registered_pairs:
            filename, category = pair
            # Try to get name from table_list.csv
            name = self._get_name_from_table_list(filename, category)
            try:
                entry = self.register(
                    filename=filename,
                    name=name,
                    category=category,
                )
                result["added"].append(entry.id)
            except Exception as e:
                logger.warning(f"Failed to register {filename}: {e}")

        # Check for updated files (hash changed)
        for entry in list(self.tables.values()):
            if not self.is_cache_valid(entry.id):
                self.update(entry.id)
                result["updated"].append(entry.id)

        return result
