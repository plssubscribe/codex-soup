"""Persistent storage helpers for the 3D design library."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .exceptions import DesignLibraryError, DesignNotFoundError
from .models import Design


class DesignStorage:
    """Manage the persistence of :class:`~design_library.models.Design` objects."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self._metadata_dir = self.root / "metadata"
        self._design_files_dir = self.root / "designs"
        self._preview_dir = self.root / "previews"
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        for directory in (self.root, self._metadata_dir, self._design_files_dir, self._preview_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------
    def add_design(
        self,
        design: Design,
        *,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        file_path: Optional[Path] = None,
    ) -> Design:
        """Persist a new design in the storage backend.

        Parameters
        ----------
        design:
            The :class:`Design` instance to persist. The design's ``identifier`` is
            used as the unique key on disk.
        file_data:
            Optional bytes representing the 3D file contents. If provided a
            ``file_name`` must also be supplied.
        file_name:
            File name to use when storing ``file_data``.
        file_path:
            An existing file on disk to import into the storage directory.
        """

        design.validate()

        metadata_path = self._metadata_path(design.identifier)
        if metadata_path.exists():
            raise DesignLibraryError(
                f"A design with identifier '{design.identifier}' already exists."
            )

        if file_data is not None and file_path is not None:
            raise DesignLibraryError(
                "Only one of 'file_data' or 'file_path' may be provided when adding a design."
            )

        if file_data is not None:
            if not file_name:
                raise DesignLibraryError(
                    "A 'file_name' must be provided when using 'file_data'."
                )
            stored_file = self._store_bytes(design.identifier, file_name, file_data)
            design.file_path = stored_file.relative_to(self.root)
            if not design.file_format:
                design.file_format = stored_file.suffix.lstrip(".")
        elif file_path is not None:
            stored_file = self._store_file(design.identifier, Path(file_path))
            design.file_path = stored_file.relative_to(self.root)
            if not design.file_format:
                design.file_format = stored_file.suffix.lstrip(".")
        else:
            stored_file = None

        design.update_timestamp()
        self._save_metadata(design)

        return design

    def import_design(
        self,
        name: str,
        description: str,
        *,
        source_path: Path,
        tags: Optional[Sequence[str]] = None,
        categories: Optional[Sequence[str]] = None,
        version: str = "1.0",
        file_format: Optional[str] = None,
        custom_attributes: Optional[dict] = None,
    ) -> Design:
        """Create and persist a design from an existing file on disk."""

        design = Design(
            name=name,
            description=description,
            tags=list(tags or []),
            categories=list(categories or []),
            version=version,
            file_format=file_format or Path(source_path).suffix.lstrip("."),
            custom_attributes=dict(custom_attributes or {}),
        )
        return self.add_design(design, file_path=Path(source_path))

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------
    def list_designs(self) -> List[Design]:
        """Return all stored designs sorted by name."""

        designs = [self._load_metadata(path) for path in sorted(self._metadata_dir.glob("*.json"))]
        return sorted(designs, key=lambda design: design.name.lower())

    def get_design(self, identifier: str) -> Design:
        """Retrieve a design by its identifier."""

        metadata_path = self._metadata_path(identifier)
        if not metadata_path.exists():
            raise DesignNotFoundError(f"Design '{identifier}' does not exist.")
        return self._load_metadata(metadata_path)

    def find_by_name(self, name: str) -> List[Design]:
        """Find designs that match the provided name (case-insensitive)."""

        name_lower = name.lower()
        return [design for design in self.list_designs() if design.name.lower() == name_lower]

    def search(
        self,
        *,
        name_query: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        categories: Optional[Iterable[str]] = None,
        file_formats: Optional[Iterable[str]] = None,
    ) -> List[Design]:
        """Search designs using multiple filters."""

        tags_set = {tag.lower() for tag in tags or []}
        categories_set = {cat.lower() for cat in categories or []}
        formats_set = {fmt.lower() for fmt in file_formats or []}
        name_query_lower = name_query.lower() if name_query else None

        results = []
        for design in self.list_designs():
            if name_query_lower and name_query_lower not in design.name.lower():
                continue
            if tags_set and not tags_set.issubset({tag.lower() for tag in design.tags}):
                continue
            if categories_set and not categories_set.issubset(
                {category.lower() for category in design.categories}
            ):
                continue
            if formats_set and design.file_format.lower() not in formats_set:
                continue
            results.append(design)
        return results

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------
    def update_design(self, identifier: str, **updates) -> Design:
        """Update a design's metadata and persist the changes."""

        design = self.get_design(identifier)
        for field, value in updates.items():
            if hasattr(design, field):
                setattr(design, field, value)
            else:
                raise DesignLibraryError(f"Unknown field '{field}' for Design")
        design.update_timestamp()
        design.validate()
        self._save_metadata(design)
        return design

    def replace_file(
        self,
        identifier: str,
        *,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        file_path: Optional[Path] = None,
    ) -> Design:
        """Replace the stored 3D file for a design."""

        design = self.get_design(identifier)

        if file_data is not None and file_path is not None:
            raise DesignLibraryError(
                "Only one of 'file_data' or 'file_path' may be provided when replacing a file."
            )

        if file_data is not None:
            if not file_name:
                raise DesignLibraryError(
                    "A 'file_name' must be provided when using 'file_data'."
                )
            stored_file = self._store_bytes(identifier, file_name, file_data, overwrite=True)
        elif file_path is not None:
            stored_file = self._store_file(identifier, Path(file_path), overwrite=True)
        else:
            raise DesignLibraryError("One of 'file_data' or 'file_path' must be provided.")

        design.file_path = stored_file.relative_to(self.root)
        design.file_format = stored_file.suffix.lstrip(".")
        design.update_timestamp()
        self._save_metadata(design)
        return design

    def attach_preview_image(self, identifier: str, image_path: Path) -> Path:
        """Attach a preview image to a design."""

        design = self.get_design(identifier)
        preview_target = self._preview_dir / identifier
        preview_target.mkdir(parents=True, exist_ok=True)
        target_file = preview_target / Path(image_path).name
        shutil.copy2(image_path, target_file)
        design.preview_image_path = target_file.relative_to(self.root)
        design.update_timestamp()
        self._save_metadata(design)
        return target_file

    # ------------------------------------------------------------------
    # Removal helpers
    # ------------------------------------------------------------------
    def remove_design(self, identifier: str, *, delete_files: bool = True) -> None:
        """Delete a design and optionally its associated files."""

        metadata_path = self._metadata_path(identifier)
        if not metadata_path.exists():
            raise DesignNotFoundError(f"Design '{identifier}' does not exist.")

        design = self._load_metadata(metadata_path)

        if delete_files:
            if design.file_path:
                absolute_file = self.root / design.file_path
                if absolute_file.exists():
                    absolute_file.unlink()
            preview_dir = self._preview_dir / identifier
            if preview_dir.exists():
                shutil.rmtree(preview_dir)
            design_dir = self._design_files_dir / identifier
            if design_dir.exists():
                shutil.rmtree(design_dir)

        metadata_path.unlink()

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _metadata_path(self, identifier: str) -> Path:
        return self._metadata_dir / f"{identifier}.json"

    def _design_directory(self, identifier: str) -> Path:
        directory = self._design_files_dir / identifier
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _store_bytes(
        self, identifier: str, filename: str, data: bytes, *, overwrite: bool = False
    ) -> Path:
        target_directory = self._design_directory(identifier)
        target_file = target_directory / filename
        if target_file.exists() and not overwrite:
            raise DesignLibraryError(
                f"A file named '{filename}' already exists for design '{identifier}'."
            )
        target_file.write_bytes(data)
        return target_file

    def _store_file(
        self, identifier: str, source: Path, *, overwrite: bool = False
    ) -> Path:
        if not source.exists():
            raise DesignLibraryError(f"Source file '{source}' does not exist.")
        target_directory = self._design_directory(identifier)
        target_file = target_directory / source.name
        if target_file.exists() and not overwrite:
            raise DesignLibraryError(
                f"A file named '{source.name}' already exists for design '{identifier}'."
            )
        shutil.copy2(source, target_file)
        return target_file

    def _save_metadata(self, design: Design) -> None:
        metadata_path = self._metadata_path(design.identifier)
        metadata_path.write_text(json.dumps(design.to_dict(), indent=2, sort_keys=True))

    def _load_metadata(self, metadata_path: Path) -> Design:
        return Design.from_dict(json.loads(metadata_path.read_text()))

    def export_design(self, identifier: str, destination: Path) -> Path:
        """Export a design's files to the destination directory."""

        design = self.get_design(identifier)
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)

        export_dir = destination / identifier
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir()

        # Copy metadata
        metadata_path = export_dir / "metadata.json"
        metadata_path.write_text(json.dumps(design.to_dict(), indent=2, sort_keys=True))

        # Copy design files
        if design.file_path:
            stored_file = self.root / design.file_path
            if stored_file.exists():
                shutil.copy2(stored_file, export_dir / stored_file.name)

        # Copy previews
        preview_dir = self._preview_dir / identifier
        if preview_dir.exists():
            destination_preview_dir = export_dir / "previews"
            shutil.copytree(preview_dir, destination_preview_dir)

        return export_dir

    def design_exists(self, identifier: str) -> bool:
        """Return whether a design exists in storage."""

        return self._metadata_path(identifier).exists()

    def clear(self) -> None:
        """Remove all designs and associated data from the storage."""

        for directory in (self._metadata_dir, self._design_files_dir, self._preview_dir):
            if directory.exists():
                shutil.rmtree(directory)
                directory.mkdir(parents=True, exist_ok=True)

    # Context manager helpers -------------------------------------------------
    def __enter__(self) -> "DesignStorage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # Nothing special to clean up
        return None
