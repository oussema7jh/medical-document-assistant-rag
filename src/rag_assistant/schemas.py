"""Validated contracts shared by answer generation, the UI, and evaluation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NO_ANSWER_MESSAGE = "I could not find this in the documents."
ERROR_MESSAGE = "The assistant could not complete this request."

AnswerStatus = Literal["answered", "no_answer", "error"]
AnswerReason = Literal[
    "empty_question",
    "question_too_long",
    "no_relevant_evidence",
    "insufficient_evidence",
    "invalid_model_output",
    "invalid_citation",
    "ungrounded_answer",
    "invalid_corpus",
    "retrieval_failed",
    "model_unavailable",
    "model_timeout",
]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]

NO_ANSWER_REASONS = frozenset(
    {
        "no_relevant_evidence",
        "insufficient_evidence",
        "invalid_model_output",
        "invalid_citation",
        "ungrounded_answer",
    }
)


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: NonEmptyText
    document_id: NonEmptyText
    document_title: NonEmptyText
    document_version: NonEmptyText
    location: NonEmptyText
    source_url: str | None = None
    supporting_excerpt: NonEmptyText
    page_number: PositiveInt | None = None
    line_start: PositiveInt | None = None
    line_end: PositiveInt | None = None

    @model_validator(mode="after")
    def check_location(self) -> Citation:
        if self.page_number is not None:
            if self.line_start is not None or self.line_end is not None:
                raise ValueError("A PDF citation has a page and no line range")
            expected = f"page {self.page_number}"
        else:
            if self.line_start is None or self.line_end is None or self.line_end < self.line_start:
                raise ValueError("A TXT citation requires an ordered line range")
            expected = f"lines {self.line_start}-{self.line_end}"
        if self.location != expected:
            raise ValueError("Location text must match the page or line range")
        return self


class AnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AnswerStatus
    answer: NonEmptyText
    citations: tuple[Citation, ...] = ()
    reason: AnswerReason | None = None
    corpus_version: NonEmptyText
    request_id: NonEmptyText

    @model_validator(mode="after")
    def check_status(self) -> AnswerResponse:
        if self.status == "answered":
            if not self.citations or self.reason is not None:
                raise ValueError("An answer requires evidence and has no failure reason")
        elif self.citations or self.reason is None:
            raise ValueError("An abstention or error requires a reason and has no citations")
        elif self.status == "no_answer":
            if self.answer != NO_ANSWER_MESSAGE or self.reason not in NO_ANSWER_REASONS:
                raise ValueError("An abstention requires the standard message and evidence reason")
        elif self.reason in NO_ANSWER_REASONS:
            raise ValueError("An error requires an operational or input failure reason")
        return self
