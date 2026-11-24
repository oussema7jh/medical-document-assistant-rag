import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval"


def run_check(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def build_manifest(tmp_path, *, status="approved", wrong_hash=False):
    documents = json.loads((DATA / "corpus_manifest.json").read_text(encoding="utf-8"))["documents"]
    rows = []
    for document_id, document in documents.items():
        rows.append(
            {
                "document_id": document_id,
                "filename": document["file"],
                "title": document["title"],
                "source_url": "https://example.org/fixture.pdf",
                "language": "fr",
                "version": document["version"],
                "sha256": "0" * 64 if wrong_hash else document["sha256"],
                "approval_status": status,
            }
        )
    manifest = tmp_path / "fixture-corpus.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return manifest


def test_existing_dataset_passes_structural_checks():
    run = run_check("validate_eval.py")
    assert run.returncode == 0, run.stderr
    assert "test: 45 answerable, 15 no-answer" in run.stdout
    assert "dev: 14 answerable, 6 no-answer" in run.stdout


def test_approved_matching_fixture_allows_only_development_export(tmp_path):
    manifest = build_manifest(tmp_path)
    development = tmp_path / "development.jsonl"
    final = tmp_path / "final.jsonl"
    run = run_check(
        "validate_eval.py",
        "--approved-manifest",
        manifest,
        "--split",
        "dev",
        "--export",
        development,
    )
    assert run.returncode == 0, run.stderr
    rows = [json.loads(line) for line in development.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 20
    assert all(row["split"] == "development" and row["id"].startswith("D-") for row in rows)
    assert all(row["location"].startswith("page ") for row in rows if row["answerable"])
    assert all(
        row["location"] is None
        and row["document_version"] is None
        and not row["alternative_sources"]
        for row in rows
        if not row["answerable"]
    )

    row = next(row for row in rows if row["id"] == "D-014")
    draft_rows = map(json.loads, (DATA / "dev.jsonl").read_text(encoding="utf-8").splitlines())
    draft = next(record for record in draft_rows if record["question_id"] == row["id"])
    documents = json.loads((DATA / "corpus_manifest.json").read_text(encoding="utf-8"))["documents"]
    assert row["expected_answer"] == draft["expected_answer"]
    assert row["document_version"] == draft["document_version"]
    assert row["alternative_sources"] == [
        {
            "document_id": "DOC-05",
            "document_version": documents["DOC-05"]["version"],
            "location": "page 14",
        }
    ]

    run = run_check(
        "validate_eval.py", "--approved-manifest", manifest, "--split", "test", "--export", final
    )
    assert run.returncode == 1
    assert "case-by-case human review" in run.stderr
    assert not final.exists()


def test_candidate_and_checksum_mismatch_block_export(tmp_path):
    output = tmp_path / "development.jsonl"
    for manifest, expected_error in (
        (build_manifest(tmp_path, status="candidate"), "is not approved"),
        (ROOT / "data" / "candidate-manifest.jsonl", "is not approved"),
    ):
        run = run_check(
            "validate_eval.py",
            "--approved-manifest",
            manifest,
            "--split",
            "dev",
            "--export",
            output,
        )
        assert run.returncode == 1
        assert expected_error in run.stderr
        assert not output.exists()
    run = run_check(
        "validate_eval.py",
        "--approved-manifest",
        build_manifest(tmp_path, wrong_hash=True),
        "--split",
        "dev",
        "--export",
        output,
    )
    assert run.returncode == 1
    assert "checksum differs" in run.stderr
    assert not output.exists()


def test_pdf_check_rejects_a_substituted_file(tmp_path):
    dataset = shutil.copytree(DATA, tmp_path / "eval")
    manifest_path = dataset / "corpus_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["documents"]["DOC-01"]["file"] = "source.pdf"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "source.pdf").write_bytes(b"unrelated fixture bytes")
    run = run_check("check_against_pdfs.py", "--pdf-dir", tmp_path, "--dir", dataset)
    assert run.returncode == 1
    assert "checksum differs" in run.stderr
