"""Data models for the 3D design library."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import uuid4

from .exceptions import DesignValidationError


@dataclass
class Design:
    """A 3D design and its metadata."""

    name: str
    description: str
    identifier: str = field(default_factory=lambda: uuid4().hex)
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    file_format: str = ""
    file_path: Optional[Path] = None
    preview_image_path: Optional[Path] = None
    custom_attributes: dict = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the design data."""

        if not self.name:
            raise DesignValidationError("Design name cannot be empty.")

        if not isinstance(self.tags, list):
            raise DesignValidationError("Tags must be a list.")

        if not isinstance(self.categories, list):
            raise DesignValidationError("Categories must be a list.")

        for value in self.tags + self.categories:
            if not isinstance(value, str):
                raise DesignValidationError("Tags and categories must be strings.")

        if self.file_format and not isinstance(self.file_format, str):
            raise DesignValidationError("file_format must be a string.")

        if self.file_path is not None and not isinstance(self.file_path, Path):
            raise DesignValidationError("file_path must be a pathlib.Path instance.")

        if self.preview_image_path is not None and not isinstance(
            self.preview_image_path, Path
        ):
            raise DesignValidationError(
                "preview_image_path must be a pathlib.Path instance."
            )

    def update_timestamp(self) -> None:
        """Update the ``updated_at`` timestamp to the current UTC time."""

        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def from_dict(cls, data: dict) -> "Design":
        """Construct a :class:`Design` from a dictionary."""

        created_at = _parse_datetime(data.get("created_at"))
        updated_at = _parse_datetime(data.get("updated_at"))
        file_path = Path(data["file_path"]) if data.get("file_path") else None
        preview_image_path = (
            Path(data["preview_image_path"])
            if data.get("preview_image_path")
            else None
        )
        design = cls(
            identifier=data.get("identifier", uuid4().hex),
            name=data["name"],
            description=data.get("description", ""),
            tags=list(data.get("tags", [])),
            categories=list(data.get("categories", [])),
            version=data.get("version", "1.0"),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
            file_format=data.get("file_format", ""),
            file_path=file_path,
            preview_image_path=preview_image_path,
            custom_attributes=dict(data.get("custom_attributes", {})),
        )
        design.validate()
        return design

    def to_dict(self) -> dict:
        """Serialize the design to a dictionary."""

        return {
            "identifier": self.identifier,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "categories": list(self.categories),
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "file_format": self.file_format,
            "file_path": str(self.file_path) if self.file_path else None,
            "preview_image_path": str(self.preview_image_path)
            if self.preview_image_path
            else None,
            "custom_attributes": dict(self.custom_attributes),
        }

    def add_tags(self, tags: Iterable[str]) -> None:
        """Add one or more tags to the design."""

        for tag in tags:
            if tag not in self.tags:
                self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if it exists."""

        if tag in self.tags:
            self.tags.remove(tag)

    def add_categories(self, categories: Iterable[str]) -> None:
        """Add one or more categories."""

        for category in categories:
            if category not in self.categories:
                self.categories.append(category)

    def remove_category(self, category: str) -> None:
        """Remove a category if it exists."""

        if category in self.categories:
            self.categories.remove(category)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise DesignValidationError(
            "Datetime values must be in ISO format."
        ) from exc
