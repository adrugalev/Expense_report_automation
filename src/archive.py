from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .utils import unique_path


def create_zip(files: list[Path], output_dir: Path, archive_name: str = "documents.zip") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = unique_path(output_dir / archive_name)
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as zip_file:
        for file_path in files:
            zip_file.write(file_path, arcname=file_path.name)
    return archive_path

