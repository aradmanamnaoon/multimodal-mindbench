"""Filesystem and streaming helpers with explicit bounds and safe output writes."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Iterator

from .schema import ValidationError


def safe_input(root: Path, relative: Path, max_bytes: int) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError("Invalid input path")
    root = root.resolve(strict=True)
    path = root / relative
    if path.is_symlink():
        raise ValidationError("Symlink inputs are not permitted")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValidationError("Input is not a regular file under dataset root")
    if resolved.stat().st_size > max_bytes:
        raise ValidationError(f"File exceeds {max_bytes} byte limit: {relative}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise ValidationError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _invalid_json_constant(value: str) -> None:
    raise ValidationError(f"Non-finite JSON token: {value}")


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f, object_pairs_hook=_unique_json_object, parse_constant=_invalid_json_constant)
    if not isinstance(data, dict):
        raise ValidationError(f"Expected JSON object: {path.name}")
    return data


def tsv_rows(path: Path, required: set[str], max_rows: int) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t", strict=True)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required.issubset(set(fields)):
            raise ValidationError(f"Invalid TSV columns in {path.name}; required={sorted(required)}")
        for i, row in enumerate(reader):
            if i >= max_rows:
                raise ValidationError(f"TSV rows exceed {max_rows}: {path.name}")
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"TSV malformed row {i + 1} in {path.name}")
            yield row


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".mindbench-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
