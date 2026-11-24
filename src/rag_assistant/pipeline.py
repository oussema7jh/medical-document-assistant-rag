"""Answer a question using the configured, approved document corpus."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .citations import InvalidSource, SourceRegistry, UnknownCitation, UnsupportedExcerpt
from .generation import (
    MAX_QUESTION_LENGTH,
    AnswerModel,
    InvalidModelOutput,
    ModelTimedOut,
    ModelUnavailable,
    build_prompt,
    generate_decision,
)
from .retrieval import retrieve
from .schemas import (
    ERROR_MESSAGE,
    NO_ANSWER_MESSAGE,
    NO_ANSWER_REASONS,
    AnswerReason,
    AnswerResponse,
)

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnswerRun:
    """The validated response and the passage IDs used to produce it."""

    response: AnswerResponse
    retrieved_chunk_ids: tuple[str, ...] = ()
    prompt_chunk_ids: tuple[str, ...] = ()


class AnswerPipeline:
    def __init__(
        self,
        index_dir: Path,
        corpus_version: str,
        manifest_path: Path,
        encoder,
        model: AnswerModel,
        *,
        max_distance: float,
        top_k: int = 5,
    ) -> None:
        if not corpus_version.strip() or corpus_version.strip() != corpus_version:
            raise ValueError("A corpus version is required")
        if not math.isfinite(max_distance) or top_k < 1:
            raise ValueError("A finite calibrated distance and positive top-k are required")
        self.index_dir = index_dir
        self.corpus_version = corpus_version
        self.manifest_path = manifest_path
        self.encoder = encoder
        self.model = model
        self.max_distance = max_distance
        self.top_k = top_k

    def answer(self, question: str) -> AnswerResponse:
        return self.answer_with_trace(question).response

    def answer_with_trace(self, question: str) -> AnswerRun:
        request = {"corpus_version": self.corpus_version, "request_id": uuid4().hex}
        retrieved_ids: tuple[str, ...] = ()
        prompt_ids: tuple[str, ...] = ()

        def failure(reason: AnswerReason) -> AnswerRun:
            no_answer = reason in NO_ANSWER_REASONS
            _logger.info("request=%s reason=%s", request["request_id"], reason)
            response = AnswerResponse(
                **request,
                status="no_answer" if no_answer else "error",
                answer=NO_ANSWER_MESSAGE if no_answer else ERROR_MESSAGE,
                reason=reason,
            )
            return AnswerRun(response, retrieved_ids, prompt_ids)

        question = question.strip()
        if not question:
            return failure("empty_question")
        if len(question) > MAX_QUESTION_LENGTH:
            return failure("question_too_long")
        try:
            registry = SourceRegistry(self.manifest_path)
        except (OSError, TypeError, ValueError, AttributeError, KeyError):
            return failure("invalid_corpus")
        try:
            hits = retrieve(
                question,
                self.corpus_version,
                self.index_dir,
                self.encoder,
                top_k=self.top_k,
                max_distance=self.max_distance,
            )
        except Exception:  # noqa: BLE001 - isolate retrieval backend failures at the service boundary
            return failure("retrieval_failed")
        retrieved_ids = tuple(hit.chunk_id for hit in hits)
        if not hits:
            return failure("no_relevant_evidence")
        try:
            registry.validate(hits)
        except InvalidSource:
            return failure("invalid_corpus")
        prompt = build_prompt(question, hits)
        prompt_ids = tuple(hit.chunk_id for hit in prompt.hits)
        if not prompt.hits:
            return failure("no_relevant_evidence")
        try:
            result = generate_decision(self.model, prompt)
        except ModelTimedOut:
            return failure("model_timeout")
        except ModelUnavailable:
            return failure("model_unavailable")
        except InvalidModelOutput:
            return failure("invalid_model_output")
        if result.status == "no_answer":
            return failure("insufficient_evidence")
        try:
            citations = registry.resolve(result.excerpts, prompt.hits)
        except UnknownCitation:
            return failure("invalid_citation")
        except UnsupportedExcerpt:
            return failure("ungrounded_answer")

        response = AnswerResponse(
            **request,
            status="answered",
            answer="\n\n".join(
                " ".join(citation.supporting_excerpt.split()) for citation in citations
            ),
            citations=citations,
        )
        return AnswerRun(response, retrieved_ids, prompt_ids)
