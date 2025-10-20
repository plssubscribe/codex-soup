# 3D Design Library

A lightweight Python library for storing and managing 3D design assets on the local filesystem. The library offers a simple API for persisting design metadata, uploading geometry files, attaching preview renders, and exporting or clearing your design archive.

## Features

- Store 3D design metadata (name, description, tags, categories, version).
- Import designs from existing geometry files or raw bytes.
- Automatically manage file-system directories for metadata, design files, and preview images.
- Search designs by name, tags, categories, or file format.
- Replace stored geometry, attach preview images, and export designs to share with collaborators.
- Comprehensive unit tests demonstrating the workflow.

## Installation

```bash
pip install -e .
```

This repository does not ship a published package, but you can install it locally in editable mode for development and experimentation.

## Usage

```python
from pathlib import Path

from design_library import Design, DesignStorage

storage = DesignStorage(Path("~/design-archive"))

# Create a new design from bytes
design = Design(
    name="Gear",
    description="A parametric gear",
    tags=["mechanical", "gear"],
    categories=["engineering"],
)

storage.add_design(design, file_data=b"STL-DATA", file_name="gear.stl")

# Fetch, update, and search designs
loaded = storage.get_design(design.identifier)
print(loaded.description)

storage.update_design(design.identifier, description="Updated description")
results = storage.search(tags=["gear"])

# Import a design from an existing file on disk
storage.import_design(
    name="Bolt",
    description="Hex bolt",
    source_path=Path("/path/to/bolt.obj"),
)

# Attach a preview image and export the design to share
storage.attach_preview_image(design.identifier, Path("preview.png"))
export_path = storage.export_design(design.identifier, Path("./exports"))
print("Design exported to", export_path)
```

## Development

Run the tests with:

```bash
pytest
```

The tests exercise the full lifecycle of adding, updating, exporting, and clearing designs, so they provide a great starting point for understanding the API surface.
