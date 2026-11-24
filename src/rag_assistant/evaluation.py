"""Run held-out questions and score source accuracy, grounding and abstention."""

from __future__ import annotations

from time import perf_counter

TARGETS = {"citation_accuracy": 0.90, "grounding_accuracy": 0.90, "abstention": 0.85}
STATUSES = {"answered", "no_answer", "error"}


def validate_final_questions(questions: list[dict]) -> None:
    if len(questions) != 60:
        raise ValueError("Expected 60 final questions")
    ids = set()
    for row in questions:
        question_id = row.get("id")
        if not isinstance(question_id, str) or not question_id.strip() or question_id in ids:
            raise ValueError("Question IDs must be nonempty and unique")
        ids.add(question_id)
        question = row.get("question")
        if row.get("split") != "final" or not isinstance(question, str) or not question.strip():
            raise ValueError(f"{question_id}: expected a nonempty final question")
        if type(row.get("answerable")) is not bool:
            raise ValueError(f"{question_id}: answerable must be a boolean")
        if row["answerable"]:
            alternatives = row.get("alternative_sources", [])
            if not isinstance(alternatives, list):
                raise ValueError(f"{question_id}: alternative sources must be a list")
            sources = [row, *alternatives]
            for source in sources:
                if not isinstance(source, dict) or not all(
                    isinstance(source.get(key), str) and source[key].strip()
                    for key in ("document_id", "location")
                ):
                    raise ValueError(f"{question_id}: source needs a document ID and location")
        elif row.get("document_id") or row.get("location") or row.get("alternative_sources"):
            raise ValueError(f"{question_id}: absent questions cannot have an expected source")
    if sum(row["answerable"] for row in questions) != 45:
        raise ValueError("Expected 45 answerable and 15 absent questions")


def run_questions(questions: list[dict], answer) -> list[dict]:
    validate_final_questions(questions)
    rows = []
    for question in questions:
        started = perf_counter()
        result = answer(question["question"])
        rows.append(
            {
                "id": question["id"],
                "question": question["question"],
                "latency_ms": round((perf_counter() - started) * 1000, 1),
                "retrieved_chunk_ids": result.retrieved_chunk_ids,
                "prompt_chunk_ids": result.prompt_chunk_ids,
                "response": result.response.model_dump(mode="json"),
            }
        )
    return rows


def _by_id(rows: list[dict], label: str) -> dict[str, dict]:
    by_id = {}
    for row in rows:
        question_id = row.get("id")
        if not isinstance(question_id, str) or not question_id.strip() or question_id in by_id:
            raise ValueError(f"{label} IDs must be nonempty and unique")
        by_id[question_id] = row
    return by_id


def _matches_source(question: dict, citation: dict) -> bool:
    for source in (question, *question.get("alternative_sources", [])):
        if (citation["document_id"], citation["location"]) != (
            source["document_id"],
            source["location"],
        ):
            continue
        if not source.get("document_version") or (
            citation.get("document_version") == source["document_version"]
        ):
            return True
    return False


def score_results(questions: list[dict], predictions: list[dict], reviews: list[dict]) -> dict:
    validate_final_questions(questions)
    predictions_by_id = _by_id(predictions, "Prediction")
    reviews_by_id = _by_id(reviews, "Review")
    question_ids = {question["id"] for question in questions}
    if set(predictions_by_id) != question_ids:
        raise ValueError("Predictions must contain exactly the final question IDs")

    cases = []
    for question in questions:
        question_id = question["id"]
        prediction = predictions_by_id[question_id]
        if prediction["question"] != question["question"]:
            raise ValueError(f"{question_id}: question differs from the frozen input")
        response = prediction["response"]
        status = response["status"]
        if status not in STATUSES:
            raise ValueError(f"{question_id}: unknown response status")
        review = reviews_by_id.pop(question_id, None)
        supported = None
        if review is not None:
            if status != "answered" or type(review.get("supported")) is not bool:
                raise ValueError(f"{question_id}: expected a boolean label for an answered case")
            reviewer = review.get("reviewer")
            if not isinstance(reviewer, str) or not reviewer.strip():
                raise ValueError(f"{question_id}: a grounding reviewer is required")
            supported = review["supported"]
        cases.append(
            {
                "id": question_id,
                "answerable": question["answerable"],
                "status": status,
                "reason": response.get("reason"),
                "source_correct": question["answerable"]
                and status == "answered"
                and any(_matches_source(question, citation) for citation in response["citations"]),
                "supported": supported,
                "grounding_note": review.get("note", "") if review else "",
                "grounding_issue": review.get("issue", "") if review else "",
                "invented_citation": response.get("reason") == "invalid_citation"
                or (
                    status == "answered"
                    and any(
                        citation["chunk_id"] not in prediction["prompt_chunk_ids"]
                        for citation in response["citations"]
                    )
                ),
            }
        )
    if reviews_by_id:
        raise ValueError(f"Unknown review IDs: {sorted(reviews_by_id)}")

    answerable = [case for case in cases if case["answerable"]]
    absent = [case for case in cases if not case["answerable"]]
    answered = [case for case in cases if case["status"] == "answered"]
    labelled = [case for case in answered if case["supported"] is not None]
    source_correct = sum(case["source_correct"] for case in answerable)
    grounded = sum(case["supported"] for case in labelled)
    correct_abstentions = sum(case["status"] == "no_answer" for case in absent)
    ratios = {
        "citation_accuracy": source_correct / len(answerable),
        "grounding_accuracy": grounded / len(answered)
        if answered and len(labelled) == len(answered)
        else None,
        "abstention": correct_abstentions / len(absent),
    }
    return {
        "counts": {
            "questions": len(cases),
            "answerable": len(answerable),
            "absent": len(absent),
            "correct_sources": source_correct,
            "answered": len(answered),
            "answered_in_scope": sum(case["status"] == "answered" for case in answerable),
            "reviewed_answers": len(labelled),
            "supported_answers": grounded,
            "correct_abstentions": correct_abstentions,
            "false_refusals": sum(case["status"] == "no_answer" for case in answerable),
            "invented_citations": sum(case["invented_citation"] for case in cases),
            "partial_answers": sum(case["grounding_issue"] == "partial_answer" for case in cases),
            "errors": sum(case["status"] == "error" for case in cases),
        },
        "metrics": ratios,
        "meets_target": {
            name: value >= TARGETS[name] if value is not None else None
            for name, value in ratios.items()
        },
        "cases": cases,
    }
