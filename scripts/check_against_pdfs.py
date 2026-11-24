"""Verify the exact source PDF files and the availability of cited pages."""

from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from validate_eval import load_dataset, source_keys


def verify_pdfs(directory: Path, manifest: dict, splits: dict[str, list[dict]]) -> None:
    citations = defaultdict(set)
    for records in splits.values():
        for record in records:
            for document_id, page in source_keys(record):
                citations[document_id].add(page)

    directory = directory.resolve(strict=True)
    fingerprints = set()
    for document_id, document in manifest["documents"].items():
        path = (directory / document["file"]).resolve(strict=True)
        if path.parent != directory or path.suffix.lower() != ".pdf":
            raise ValueError(f"{document_id}: expected a PDF inside the source directory")
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            if checksum != document["sha256"]:
                raise ValueError(f"{document_id}: checksum differs from the dataset manifest")
            if checksum in fingerprints:
                raise ValueError(f"{document_id}: duplicate source PDF")
            fingerprints.add(checksum)
            stream.seek(0)
            reader = PdfReader(stream)
            if len(reader.pages) != document["pages"]:
                raise ValueError(f"{document_id}: PDF page count differs from the dataset manifest")
            for page in sorted(citations[document_id]):
                if not (reader.pages[page - 1].extract_text() or "").strip():
                    raise ValueError(f"{document_id}: cited page {page} has no extractable text")
    print(
        f"Verified {len(fingerprints)} PDF checksums and {sum(map(len, citations.values()))} cited pages."
    )
    print("Expected answers and absent cases still require case-by-case human verification.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--dir", type=Path, default=Path("data/eval"))
    args = parser.parse_args()
    try:
        manifest, splits = load_dataset(args.dir)
        verify_pdfs(args.pdf_dir, manifest, splits)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, PdfReadError) as error:
        parser.exit(1, f"PDF source check failed: {error}\n")


if __name__ == "__main__":
    main()
