from copy import deepcopy
from types import SimpleNamespace

import pytest

from rag_assistant.evaluation import run_questions, score_results, validate_final_questions


def final_questions():
    return [
        {
            "id": f"T-{number:03d}",
            "question": f"Synthetic question {number}?",
            "split": "final",
            "answerable": number < 45,
            "document_id": "synthetic" if number < 45 else None,
            "document_version": "1" if number < 45 else None,
            "location": "page 2" if number < 45 else None,
        }
        for number in range(60)
    ]


def predictions(questions):
    def answer(question):
        case = next(row for row in questions if row["question"] == question)
        citation = {
            "chunk_id": "source-chunk",
            "document_id": "synthetic",
            "document_version": "1",
            "location": "page 2",
        }
        payload = {
            "status": "answered" if case["answerable"] else "no_answer",
            "citations": [citation] if case["answerable"] else [],
        }
        return SimpleNamespace(
            response=SimpleNamespace(model_dump=lambda *, mode: payload),
            retrieved_chunk_ids=("source-chunk",),
            prompt_chunk_ids=("source-chunk",),
        )

    return run_questions(questions, answer)


def test_freeze_counts_and_development_exclusion():
    questions = final_questions()
    validate_final_questions(questions)
    questions[1]["split"] = "development"
    with pytest.raises(ValueError, match="final question"):
        validate_final_questions(questions)


def test_scores_human_review_exact_page_and_true_abstention():
    questions = final_questions()
    rows = predictions(questions)
    rows[0]["response"]["citations"][0]["location"] = "page 3"
    rows[1]["response"] = {"status": "no_answer", "reason": "invalid_citation"}
    rows[-1]["response"] = {"status": "error", "reason": "model_timeout"}
    reviews = [
        {
            "id": question["id"],
            "reviewer": "fixture",
            "supported": number != 2,
            "issue": "partial_answer" if number == 2 else "",
        }
        for number, question in enumerate(questions[:45])
        if number != 1
    ]
    provisional = score_results(questions, rows, reviews[:-1])
    assert provisional["metrics"]["grounding_accuracy"] is None
    result = score_results(questions, rows, reviews)
    assert result["metrics"] == {
        "citation_accuracy": 43 / 45,
        "grounding_accuracy": 43 / 44,
        "abstention": 14 / 15,
    }
    assert result["counts"]["invented_citations"] == 1
    assert result["counts"]["partial_answers"] == 1
    assert result["counts"]["false_refusals"] == 1
    assert result["counts"]["errors"] == 1


def test_duplicate_predictions_and_changed_frozen_questions_fail():
    questions = final_questions()
    rows = predictions(questions)
    with pytest.raises(ValueError, match="unique"):
        score_results(questions, rows + [deepcopy(rows[0])], [])
    rows[0]["question"] = "Different question?"
    with pytest.raises(ValueError, match="frozen input"):
        score_results(questions, rows, [])
