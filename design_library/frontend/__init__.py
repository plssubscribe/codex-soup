"""Web frontend for browsing and managing 3D designs."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

from flask import (
    Flask,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from ..models import Design
from ..storage import DesignStorage


def create_app(storage_root: str | os.PathLike[str] | None = None) -> Flask:
    """Create and configure the design library frontend application."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.setdefault("SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "dev"))

    if storage_root is None:
        storage_root = Path(os.environ.get("DESIGN_LIBRARY_ROOT", app.instance_path)) / "designs"
    storage_path = Path(storage_root).expanduser().resolve()
    storage_path.mkdir(parents=True, exist_ok=True)

    app.config["DESIGN_STORAGE"] = DesignStorage(storage_path)

    @app.context_processor
    def inject_utilities() -> dict[str, object]:
        return {
            "format_datetime": _format_datetime,
        }

    @app.route("/")
    def index() -> str:
        storage = _storage()
        query = request.args.get("q", "").strip()
        tags = _split_csv(request.args.get("tags", ""))
        categories = _split_csv(request.args.get("categories", ""))
        file_formats = _split_csv(request.args.get("formats", ""))

        if any([query, tags, categories, file_formats]):
            designs = storage.search(
                name_query=query or None,
                tags=tags or None,
                categories=categories or None,
                file_formats=file_formats or None,
            )
            search_performed = True
        else:
            designs = storage.list_designs()
            search_performed = False

        decorated = [_decorate_design(design) for design in designs]
        return render_template(
            "index.html",
            designs=decorated,
            search_performed=search_performed,
            query=query,
            tags=", ".join(tags),
            categories=", ".join(categories),
            file_formats=", ".join(file_formats),
        )

    @app.route("/designs/new", methods=["GET", "POST"])
    def create_design() -> str | Response:
        storage = _storage()
        if request.method == "POST":
            form = request.form
            name = form.get("name", "").strip()
            description = form.get("description", "").strip()
            if not name:
                flash("A design name is required.", "error")
                return redirect(url_for("create_design"))

            tags = _split_csv(form.get("tags", ""))
            categories = _split_csv(form.get("categories", ""))
            version = form.get("version", "1.0").strip() or "1.0"
            file_format = form.get("file_format", "").strip()
            custom_attributes = _parse_custom_attributes(form.get("custom_attributes", ""))

            design = Design(
                name=name,
                description=description,
                tags=tags,
                categories=categories,
                version=version,
                file_format=file_format,
                custom_attributes=custom_attributes,
            )

            design_file = request.files.get("design_file")
            try:
                if design_file and design_file.filename:
                    filename = secure_filename(design_file.filename)
                    storage.add_design(
                        design,
                        file_data=design_file.read(),
                        file_name=filename,
                    )
                else:
                    storage.add_design(design)
            except Exception as exc:  # noqa: BLE001 - surface storage errors to UI
                flash(str(exc), "error")
                return redirect(url_for("create_design"))

            flash("Design created successfully!", "success")
            return redirect(url_for("design_detail", identifier=design.identifier))

        return render_template("create_design.html")

    @app.route("/designs/<identifier>")
    def design_detail(identifier: str) -> str:
        storage = _storage()
        design = storage.get_design(identifier)
        return render_template("detail.html", design=_decorate_design(design))

    @app.route("/designs/<identifier>/update", methods=["POST"])
    def update_design(identifier: str) -> Response:
        storage = _storage()
        form = request.form
        tags = _split_csv(form.get("tags", ""))
        categories = _split_csv(form.get("categories", ""))
        custom_attributes = _parse_custom_attributes(form.get("custom_attributes", ""))

        updates: dict[str, object] = {
            "name": form.get("name", "").strip(),
            "description": form.get("description", "").strip(),
            "version": form.get("version", "1.0").strip() or "1.0",
            "tags": tags,
            "categories": categories,
            "custom_attributes": custom_attributes,
        }
        file_format = form.get("file_format", "").strip()
        if file_format:
            updates["file_format"] = file_format

        updates = {key: value for key, value in updates.items() if value is not None}

        try:
            storage.update_design(identifier, **updates)
        except Exception as exc:  # noqa: BLE001 - present to user
            flash(str(exc), "error")
        else:
            flash("Design updated successfully.", "success")
        return redirect(url_for("design_detail", identifier=identifier))

    @app.route("/designs/<identifier>/replace-file", methods=["POST"])
    def replace_file(identifier: str) -> Response:
        storage = _storage()
        design_file = request.files.get("design_file")
        if not design_file or not design_file.filename:
            flash("Upload a file to replace the existing geometry.", "error")
            return redirect(url_for("design_detail", identifier=identifier))

        filename = secure_filename(design_file.filename)
        try:
            storage.replace_file(
                identifier,
                file_data=design_file.read(),
                file_name=filename,
            )
        except Exception as exc:  # noqa: BLE001 - user feedback
            flash(str(exc), "error")
        else:
            flash("Design file replaced successfully.", "success")
        return redirect(url_for("design_detail", identifier=identifier))

    @app.route("/designs/<identifier>/upload-preview", methods=["POST"])
    def upload_preview(identifier: str) -> Response:
        storage = _storage()
        preview = request.files.get("preview_image")
        if not preview or not preview.filename:
            flash("Choose an image to upload as a preview.", "error")
            return redirect(url_for("design_detail", identifier=identifier))

        filename = secure_filename(preview.filename)
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            temp_path = temp_dir / filename
            preview.save(temp_path)
            try:
                storage.attach_preview_image(identifier, temp_path)
            except Exception as exc:  # noqa: BLE001
                flash(str(exc), "error")
            else:
                flash("Preview uploaded successfully.", "success")
        return redirect(url_for("design_detail", identifier=identifier))

    @app.route("/designs/<identifier>/delete", methods=["POST"])
    def delete_design(identifier: str) -> Response:
        storage = _storage()
        try:
            storage.remove_design(identifier)
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")
            return redirect(url_for("design_detail", identifier=identifier))
        flash("Design deleted.", "success")
        return redirect(url_for("index"))

    @app.route("/designs/<identifier>/download")
    def download_design_file(identifier: str) -> Response:
        design = _storage().get_design(identifier)
        if not design.file_path:
            flash("This design does not have a stored file yet.", "error")
            return redirect(url_for("design_detail", identifier=identifier))
        file_path = _storage_root() / design.file_path
        if not file_path.exists():
            flash("Stored file is missing on disk.", "error")
            return redirect(url_for("design_detail", identifier=identifier))
        return send_from_directory(file_path.parent, file_path.name, as_attachment=True)

    @app.route("/designs/<identifier>/preview/<path:filename>")
    def serve_preview(identifier: str, filename: str) -> Response:
        preview_dir = _storage_root() / "previews" / identifier
        return send_from_directory(preview_dir, filename)

    @app.route("/designs/<identifier>/export")
    def export_design(identifier: str) -> Response:
        storage = _storage()
        with tempfile.TemporaryDirectory() as tmpdir:
            export_root = Path(tmpdir)
            export_path = storage.export_design(identifier, export_root)
            archive_path = shutil.make_archive(str(export_path), "zip", export_path)
            directory = Path(archive_path).parent
            filename = Path(archive_path).name
        return send_from_directory(directory, filename, as_attachment=True)

    @app.route("/files/<identifier>/<path:filename>")
    def serve_file(identifier: str, filename: str) -> Response:
        design_dir = _storage_root() / "designs" / identifier
        return send_from_directory(design_dir, filename)

    return app


def _storage() -> DesignStorage:
    return current_app.config["DESIGN_STORAGE"]


def _storage_root() -> Path:
    return _storage().root


def _split_csv(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def _parse_custom_attributes(raw: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            continue
        attributes[key] = value.strip()
    return attributes


def _decorate_design(design: Design) -> dict[str, object]:
    data = asdict(design)
    data["preview_urls"] = []
    storage_root = _storage_root()
    preview_dir = storage_root / "previews" / design.identifier
    if preview_dir.exists():
        for preview_file in sorted(preview_dir.iterdir()):
            if preview_file.is_file():
                data["preview_urls"].append(
                    url_for("serve_preview", identifier=design.identifier, filename=preview_file.name)
                )
    if design.file_path:
        data["download_url"] = url_for("download_design_file", identifier=design.identifier)
        data["file_url"] = url_for(
            "serve_file", identifier=design.identifier, filename=design.file_path.name
        )
    else:
        data["download_url"] = None
        data["file_url"] = None
    data["detail_url"] = url_for("design_detail", identifier=design.identifier)
    data["updated_at_human"] = _format_datetime(design.updated_at)
    data["created_at_human"] = _format_datetime(design.created_at)
    return data


def _format_datetime(value) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")
