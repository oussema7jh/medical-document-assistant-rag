import pytest
from pydantic import ValidationError

from rag_assistant.schemas import NO_ANSWER_MESSAGE, AnswerResponse, Citation


def test_citation_locations_agree_with_their_metadata():
    evidence = {
        "chunk_id": "chunk-01",
        "document_id": "orientation",
        "document_title": "Staff orientation",
        "document_version": "2026",
        "supporting_excerpt": "The orientation starts at 9 a.m.",
    }
    assert Citation(**evidence, location="page 2", page_number=2).line_start is None
    assert Citation(**evidence, location="lines 1-2", line_start=1, line_end=2).page_number is None
    with pytest.raises(ValidationError):
        Citation(**evidence, location="page 2", page_number=3)
    with pytest.raises(ValidationError):
        Citation(**evidence, location="page 0", page_number=0)
    with pytest.raises(ValidationError):
        Citation(**evidence, location="lines 2-1", line_start=2, line_end=1)


def test_answer_requires_sources_and_abstention_requires_a_supported_reason():
    common = {"corpus_version": "v1", "request_id": "request-1"}
    response = AnswerResponse(
        **common,
        status="no_answer",
        answer=NO_ANSWER_MESSAGE,
        reason="no_relevant_evidence",
    )
    assert response.model_dump(mode="json")["citations"] == []
    with pytest.raises(ValidationError):
        AnswerResponse(**common, status="answered", answer="A claim with no citations.")
    with pytest.raises(ValidationError):
        AnswerResponse(
            **common, status="no_answer", answer=NO_ANSWER_MESSAGE, reason="model_unavailable"
        )
