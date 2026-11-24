"""Validate the evaluation draft and export only against the exact approved corpus."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

REQUIRED = {
    "question_id",
    "split",
    "question",
    "expected_answer",
    "answerable",
    "document_id",
    "document_version",
    "page",
    "alt_sources",
    "question_type",
    "no_answer_type",
    "notes",
    "status",
    "reviewed_by",
    "dataset_version",
}
NO_ANSWER_TYPES = {"near_miss", "related_gap", "out_of_scope"}


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def normalize(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def source_keys(record: dict) -> list[tuple[str, int]]:
    if not record["answerable"]:
        return []
    return [(record["document_id"], record["page"])] + [
        (source["document_id"], source["page"]) for source in record["alt_sources"]
    ]


def validate_csv(path: Path, records: list[dict]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(records):
        raise ValueError(f"{path}: CSV and JSONL row counts differ")
    for row, record in zip(rows, records, strict=True):
        if set(row) != set(record):
            raise ValueError(f"{path}: CSV and JSONL columns differ")
        for key, expected in record.items():
            cell = row[key]
            if isinstance(expected, list):
                matches = json.loads(cell) == expected
            else:
                matches = cell == ("" if expected is None else str(expected))
            if not matches:
                raise ValueError(f"{path}: {record['question_id']} differs in {key}")


def validate_record(record: dict, split: str, manifest: dict) -> None:
    question_id = record.get("question_id", "<missing question_id>")
    missing = REQUIRED - record.keys()
    if missing:
        raise ValueError(f"{question_id}: missing fields {sorted(missing)}")
    prefix = "D-" if split == "dev" else "T-"
    if record["split"] != split or not question_id.startswith(prefix):
        raise ValueError(f"{question_id}: expected a {split} record with prefix {prefix}")
    if record["dataset_version"] != manifest["dataset_version"]:
        raise ValueError(f"{question_id}: dataset version differs from manifest")
    if not record["question"].strip() or not record["expected_answer"].strip():
        raise ValueError(f"{question_id}: empty question or expected result")
    if type(record["answerable"]) is not bool or not isinstance(record["alt_sources"], list):
        raise ValueError(f"{question_id}: expected a boolean answerable and list alt_sources")

    documents = manifest["documents"]
    if record["answerable"]:
        document = documents.get(record["document_id"])
        if document is None or document["version"] != record["document_version"]:
            raise ValueError(f"{question_id}: primary document or version differs from manifest")
        if record["no_answer_type"] is not None:
            raise ValueError(f"{question_id}: answerable record has a no-answer category")
        for document_id, page in source_keys(record):
            document = documents.get(document_id)
            if document is None or type(page) is not int or not 1 <= page <= document["pages"]:
                raise ValueError(f"{question_id}: invalid source {document_id!r} page {page!r}")
    elif (
        any(record[key] is not None for key in ("document_id", "document_version", "page"))
        or record["alt_sources"]
        or record["no_answer_type"] not in NO_ANSWER_TYPES
    ):
        raise ValueError(f"{question_id}: no-answer record has a source or invalid category")


def load_dataset(directory: Path) -> tuple[dict, dict[str, list[dict]]]:
    manifest = json.loads((directory / "corpus_manifest.json").read_text(encoding="utf-8"))
    for document_id, document in manifest["documents"].items():
        if (
            not re.fullmatch(r"[0-9a-f]{64}", document["sha256"])
            or type(document["pages"]) is not int
            or document["pages"] < 1
        ):
            raise ValueError(f"{document_id}: invalid corpus checksum or page count")
    splits = {}
    questions = set()
    ids = set()
    for split in ("dev", "test"):
        records = read_jsonl(directory / f"{split}.jsonl")
        for record in records:
            validate_record(record, split, manifest)
            question = normalize(record["question"])
            question_id = record["question_id"]
            if question_id in ids or question in questions:
                raise ValueError(f"{question_id}: duplicate question ID or normalized question")
            ids.add(question_id)
            questions.add(question)
        validate_csv(directory / f"{split}.csv", records)
        splits[split] = records

    test_counts = Counter(record["answerable"] for record in splits["test"])
    if test_counts != {True: 45, False: 15}:
        raise ValueError(f"Test set requires 45 answerable and 15 no-answer rows: {test_counts}")
    dev_counts = Counter(record["answerable"] for record in splits["dev"])
    if dev_counts[True] < 10 or dev_counts[False] < 4:
        raise ValueError("Development set requires at least 10 answerable and 4 no-answer examples")

    def passage_answers(records: list[dict]) -> set[tuple]:
        return {
            (document_id, page, normalize(record["expected_answer"]))
            for record in records
            for document_id, page in source_keys(record)
        }

    if passage_answers(splits["dev"]) & passage_answers(splits["test"]):
        raise ValueError("Development and test sets share a normalized answer and source page")
    return manifest, splits


def verify_approved_manifest(path: Path, documents: dict) -> None:
    from rag_assistant.ingestion import load_manifest

    approved = load_manifest(path)
    by_id = {entry["document_id"]: entry for entry in approved}
    if len(by_id) != len(approved) or set(by_id) != set(documents):
        raise ValueError(
            "Approved corpus document IDs differ from the dataset corpus; revalidate all rows"
        )
    for document_id, draft in documents.items():
        selected = by_id[document_id]
        if any(selected[key] != draft[key] for key in ("version", "sha256")):
            raise ValueError(
                f"{document_id}: approved corpus version or checksum differs from dataset"
            )


def export_records(records: list[dict], documents: dict, split: str, output: Path) -> None:
    if split == "test" and any(
        record["status"] != "reviewed" or not (record["reviewed_by"] or "").strip()
        for record in records
    ):
        raise ValueError("Final export requires recorded case-by-case human review")

    rows = []
    for record in records:
        page = record["page"]
        rows.append(
            {
                "id": record["question_id"],
                "split": "development" if split == "dev" else "final",
                "question": record["question"],
                "expected_answer": record["expected_answer"],
                "answerable": record["answerable"],
                "document_id": record["document_id"],
                "document_version": record["document_version"],
                "location": f"page {page}" if page is not None else None,
                "alternative_sources": [
                    {
                        "document_id": source["document_id"],
                        "document_version": documents[source["document_id"]]["version"],
                        "location": f"page {source['page']}",
                    }
                    for source in record["alt_sources"]
                ],
                "dataset_version": record["dataset_version"],
            }
        )
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path("data/eval"))
    parser.add_argument("--approved-manifest", type=Path)
    parser.add_argument("--export", type=Path, help="Write evaluator input to a new file")
    parser.add_argument("--split", choices=("dev", "test"))
    args = parser.parse_args()
    if args.export and (not args.approved_manifest or not args.split):
        parser.error("--export requires --approved-manifest and --split")
    if args.split and not args.export:
        parser.error("--split requires --export")

    try:
        manifest, splits = load_dataset(args.dir)
        for split, records in splits.items():
            counts = Counter(record["answerable"] for record in records)
            statuses = Counter(record["status"] for record in records)
            print(
                f"{split}: {counts[True]} answerable, {counts[False]} no-answer; {dict(statuses)}"
            )
        if args.approved_manifest:
            verify_approved_manifest(args.approved_manifest, manifest["documents"])
        if args.export:
            export_records(splits[args.split], manifest["documents"], args.split, args.export)
            print(f"Wrote {args.export}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(1, f"Evaluation dataset check failed: {error}\n")
    print("Structural checks passed.")


if __name__ == "__main__":
    main()
