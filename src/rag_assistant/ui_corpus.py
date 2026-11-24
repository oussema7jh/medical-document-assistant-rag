"""Local corpus operations for the Streamlit interface."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory

from .chunking import Chunk, chunk_records
from .index import collection_name
from .ingestion import extract_document, load_manifest

MAX_UPLOAD_BYTES = 20_000_000


def available_versions(index_dir: Path) -> dict[str, dict]:
    versions = {}
    for path in sorted(index_dir.glob("corpus_*.json")):
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
            version = metadata["corpus_version"]
            name = collection_name(version)
            if path.stem == metadata["collection"] == name:
                versions[version] = metadata
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return versions


def retrieval_settings(calibration_path: Path, metadata: dict) -> tuple[int, float]:
    report = json.loads(calibration_path.read_text(encoding="utf-8"))
    for key in ("corpus_version", "encoder", "revision"):
        if report[key] != metadata[key]:
            raise ValueError("Calibration does not match the active corpus and encoder")
    chosen = report["chosen"]
    top_k, cutoff = chosen["top_k"], chosen["max_distance"]
    if (
        type(top_k) is not int
        or top_k < 1
        or type(cutoff) not in (int, float)
        or not math.isfinite(cutoff)
    ):
        raise ValueError("Calibration settings are invalid")
    return top_k, float(cutoff)


def prepare_import(
    files: Mapping[str, bytes | memoryview],
    manifest_path: Path,
    index_dir: Path,
    version: str,
) -> tuple[list[Chunk], int]:
    """Validate and extract local uploads without changing the active index."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise ValueError("Use 1–64 letters, numbers, dots, hyphens or underscores for the version.")
    if not files:
        raise ValueError("Choose at least one approved PDF or TXT file.")
    if version in available_versions(index_dir):
        raise ValueError("That corpus version already exists. Choose a new version.")

    approved = {}
    for record in load_manifest(manifest_path):
        key = (record["filename"], record["sha256"])
        if key in approved:
            raise ValueError("More than one approved record represents the same file.")
        approved[key] = record

    selected = []
    checksums = set()
    for name, contents in files.items():
        if len(contents) > MAX_UPLOAD_BYTES:
            raise ValueError(f"{name} is over the 20 MB limit.")
        checksum = hashlib.sha256(contents).hexdigest()
        record = approved.get((name, checksum))
        if record is None:
            raise ValueError(f"{name} does not match an approved filename and checksum.")
        if checksum in checksums:
            raise ValueError(f"{name} duplicates another uploaded file.")
        checksums.add(checksum)
        selected.append((record, contents))

    pages = []
    with TemporaryDirectory(prefix="rag-import-") as temporary:
        staging = Path(temporary)
        for record, contents in selected:
            path = staging / record["filename"]
            path.write_bytes(contents)
            try:
                extracted = extract_document(record, staging, max_bytes=MAX_UPLOAD_BYTES)
            except Exception as exc:
                raise ValueError(
                    f"Could not read {path.name} as an approved PDF or TXT file."
                ) from exc
            if not any(page.status == "ok" for page in extracted):
                raise ValueError(f"No readable text was found in {path.name}.")
            pages.extend(extracted)

    return chunk_records(pages, version), sum(page.status != "ok" for page in pages)
