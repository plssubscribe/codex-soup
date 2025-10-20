from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from design_library import Design, DesignNotFoundError, DesignStorage


def test_add_and_list_designs(tmp_path: Path) -> None:
    storage = DesignStorage(tmp_path)

    design = Design(
        name="Sample Gear",
        description="A simple gear model",
        tags=["mechanical", "gear"],
        categories=["engineering"],
        version="1.0",
    )

    storage.add_design(design, file_data=b"content", file_name="gear.stl")

    listed = storage.list_designs()
    assert len(listed) == 1
    assert listed[0].name == "Sample Gear"
    assert listed[0].file_path is not None

    loaded = storage.get_design(design.identifier)
    assert loaded.description == "A simple gear model"
    assert (tmp_path / loaded.file_path).exists()

    search_results = storage.search(tags=["gear"])
    assert len(search_results) == 1
    assert search_results[0].identifier == design.identifier


def test_update_and_replace_file(tmp_path: Path) -> None:
    storage = DesignStorage(tmp_path)
    design = Design(name="Widget", description="Original")
    storage.add_design(design, file_data=b"abc", file_name="widget.stl")

    updated = storage.update_design(design.identifier, description="Updated")
    assert updated.description == "Updated"

    storage.replace_file(design.identifier, file_data=b"new", file_name="widget.stl")
    stored_file = tmp_path / updated.file_path
    assert stored_file.read_bytes() == b"new"


def test_attach_preview_and_export(tmp_path: Path) -> None:
    storage = DesignStorage(tmp_path)
    design = Design(name="Bolt", description="Hex bolt")
    storage.add_design(design, file_data=b"bolt", file_name="bolt.obj")

    preview_source = tmp_path / "preview.png"
    preview_source.write_bytes(b"image")
    preview_path = storage.attach_preview_image(design.identifier, preview_source)
    assert preview_path.exists()

    export_dir = storage.export_design(design.identifier, tmp_path / "export")
    assert (export_dir / "metadata.json").exists()
    assert any(file.suffix == ".obj" for file in export_dir.iterdir())
    assert (export_dir / "previews" / preview_source.name).exists()


def test_remove_design(tmp_path: Path) -> None:
    storage = DesignStorage(tmp_path)
    design = Design(name="Bracket", description="Support bracket")
    storage.add_design(design, file_data=b"bracket", file_name="bracket.obj")
    identifier = design.identifier

    storage.remove_design(identifier)

    with pytest.raises(DesignNotFoundError):
        storage.get_design(identifier)


def test_import_design(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    source_file = source_dir / "engine.fbx"
    source_file.write_bytes(b"engine")

    storage = DesignStorage(tmp_path)
    design = storage.import_design(
        name="Engine",
        description="Engine assembly",
        source_path=source_file,
        tags=["mechanical"],
        categories=["automotive"],
        version="2.0",
    )

    stored_file = tmp_path / design.file_path
    assert stored_file.exists()
    assert stored_file.read_bytes() == b"engine"


def test_design_exists_and_clear(tmp_path: Path) -> None:
    storage = DesignStorage(tmp_path)
    design = Design(name="Housing", description="Plastic housing")
    storage.add_design(design, file_data=b"housing", file_name="housing.stl")

    assert storage.design_exists(design.identifier)

    storage.clear()

    assert not storage.design_exists(design.identifier)
    assert storage.list_designs() == []
