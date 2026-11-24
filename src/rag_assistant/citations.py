"""Resolve source metadata using only the approved manifest and provided evidence."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

from .generation import ExcerptSelection
from .ingestion import load_manifest
from .retrieval import Hit
from .schemas import Citation


class InvalidSource(ValueError):
    """A retrieved passage cannot be mapped to the approved corpus."""


class UnknownCitation(ValueError):
    """The model cited an ID outside the exact prompt evidence."""


class UnsupportedExcerpt(ValueError):
    """The claimed excerpt is absent from the cited passage."""


class SourceRegistry:
    def __init__(self, manifest_path: Path) -> None:
        self._documents = {
            (record["document_id"], record["version"]): record
            for record in load_manifest(manifest_path)
        }

    def _metadata(self, hit: Hit) -> dict:
        record = self._documents.get((hit.document_id, hit.version))
        if record is None or not isinstance(record["title"], str) or not record["title"].strip():
            raise InvalidSource("The passage has no approved document and version")

        page = re.fullmatch(r"page ([1-9]\d*)", hit.location)
        lines = re.fullmatch(r"lines ([1-9]\d*)-([1-9]\d*)", hit.location)
        extension = Path(record["filename"]).suffix.lower()
        if extension == ".pdf" and page:
            location = {"page_number": int(page[1])}
        elif extension == ".txt" and lines and int(lines[1]) <= int(lines[2]):
            location = {"line_start": int(lines[1]), "line_end": int(lines[2])}
        else:
            raise InvalidSource("The passage has an invalid page or line location")

        url = record["source_url"]
        source_url = None
        if isinstance(url, str):
            try:
                parsed = urlsplit(url)
            except ValueError:
                pass
            else:
                if (
                    parsed.scheme in {"https", "http"}
                    and parsed.hostname
                    and parsed.username is None
                    and parsed.password is None
                ):
                    source_url = url
        return {"document_title": record["title"], "source_url": source_url, **location}

    def validate(self, hits: Sequence[Hit]) -> None:
        for hit in hits:
            self._metadata(hit)

    def resolve(
        self, excerpts: Sequence[ExcerptSelection], allowed: Sequence[Hit]
    ) -> tuple[Citation, ...]:
        hits = {hit.chunk_id: hit for hit in allowed}
        citations = []
        seen: set[tuple[str, str, str, str]] = set()
        for selection in excerpts:
            hit = hits.get(selection.chunk_id)
            if hit is None:
                raise UnknownCitation("The excerpt references an ID outside the prompt")
            original = _source_excerpt(selection.quote, hit.text)
            if original is None:
                raise UnsupportedExcerpt("The selected quote is not a complete source excerpt")
            key = (hit.document_id, hit.version, hit.location, " ".join(original.split()))
            if key not in seen:
                citations.append(
                    Citation(
                        chunk_id=hit.chunk_id,
                        document_id=hit.document_id,
                        document_version=hit.version,
                        location=hit.location,
                        supporting_excerpt=original,
                        **self._metadata(hit),
                    )
                )
                seen.add(key)
        return tuple(citations)


def _source_excerpt(quote: str, passage: str) -> str | None:
    # PDF layout whitespace may differ in the model's copy. Preserve the actual source text.
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    for match in re.finditer(pattern, passage):
        before = passage[: match.start()].rstrip()
        after = passage[match.end() :]
        if before and (not passage[match.start() - 1].isspace() or before[-1] not in ".!?"):
            continue
        if after and (not after[0].isspace() or match[0][-1] not in ".!?"):
            continue
        return match[0]
    return None
