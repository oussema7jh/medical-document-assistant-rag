"""Run the frozen answer benchmark and score it after human grounding review."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from rag_assistant.evaluation import run_questions, score_results, validate_final_questions


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(content, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def run(args: argparse.Namespace, questions: list[dict]) -> None:
    from rag_assistant import generation, pipeline
    from rag_assistant.embeddings import Encoder
    from rag_assistant.index import collection_name
    from rag_assistant.ingestion import load_manifest

    if args.output.exists():
        raise FileExistsError(args.output)
    if not math.isfinite(args.max_distance) or args.top_k < 1:
        raise ValueError("Expected a finite distance limit and positive top-k")
    documents: dict[str, set[str]] = {}
    for record in load_manifest(args.manifest):
        documents.setdefault(record["document_id"], set()).add(record["version"])
    for question in questions:
        if not question["answerable"]:
            continue
        for source in (question, *question.get("alternative_sources", [])):
            versions = documents.get(source["document_id"], set())
            version = source.get("document_version")
            if not versions or (version and version not in versions):
                raise ValueError(
                    f"{question['id']}: expected source is outside the approved corpus"
                )
    index_manifest = args.index_dir / f"{collection_name(args.corpus_version)}.json"
    config = {
        "question_sha256": sha256(args.questions),
        "manifest_sha256": sha256(args.manifest),
        "index_manifest_sha256": sha256(index_manifest),
        "corpus_version": args.corpus_version,
        "model": args.model,
        "top_k": args.top_k,
        "max_distance": args.max_distance,
    }
    assistant = pipeline.AnswerPipeline(
        args.index_dir,
        args.corpus_version,
        args.manifest,
        Encoder(),
        generation.OllamaModel(args.model),
        max_distance=args.max_distance,
        top_k=args.top_k,
    )
    rows = run_questions(questions, assistant.answer_with_trace)
    timings = sorted(row["latency_ms"] for row in rows)
    config["median_latency_ms"] = statistics.median(timings)
    config["p95_latency_ms"] = timings[math.ceil(0.95 * len(timings)) - 1]
    write_json(args.output, {"configuration": config, "predictions": rows})


def score(args: argparse.Namespace, questions: list[dict]) -> None:
    results = json.loads(args.results.read_text(encoding="utf-8"))
    config = results["configuration"]
    if config["question_sha256"] != sha256(args.questions):
        raise ValueError("Question file differs from the file used for the frozen run")
    reviews = read_jsonl(args.reviews) if args.reviews else []
    run_hash = sha256(args.results)
    if any(review.get("run_sha256") != run_hash for review in reviews):
        raise ValueError("Each review must name the SHA-256 of the specific raw run it reviewed")
    scored = score_results(questions, results["predictions"], reviews)
    write_json(args.output, {"configuration": config, **scored})
    print(json.dumps(scored["counts"], indent=2))
    print(json.dumps(scored["metrics"], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("questions", type=Path)
    runner.add_argument("manifest", type=Path)
    runner.add_argument("index_dir", type=Path)
    runner.add_argument("corpus_version")
    runner.add_argument("output", type=Path)
    runner.add_argument("--model", required=True)
    runner.add_argument("--top-k", type=int, required=True)
    runner.add_argument("--max-distance", type=float, required=True)
    scorer = commands.add_parser("score")
    scorer.add_argument("questions", type=Path)
    scorer.add_argument("results", type=Path)
    scorer.add_argument("output", type=Path)
    scorer.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    questions = read_jsonl(args.questions)
    validate_final_questions(questions)
    (run if args.command == "run" else score)(args, questions)


if __name__ == "__main__":
    main()
