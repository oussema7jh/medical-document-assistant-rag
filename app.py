"""Streamlit entry point for the medical document assistant."""

from __future__ import annotations

import hashlib
import os
import re
from html import escape
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import streamlit as st

from rag_assistant.embeddings import Encoder
from rag_assistant.generation import MAX_QUESTION_LENGTH
from rag_assistant.index import build_index
from rag_assistant.ingestion import load_manifest
from rag_assistant.ui_corpus import available_versions, prepare_import, retrieval_settings

if TYPE_CHECKING:
    from rag_assistant.schemas import AnswerResponse


PROTOTYPE_NOTICE = "Prototype — not for medical use"
ERROR_MESSAGES = {
    "empty_question": "Enter a question to search the documents.",
    "question_too_long": "Shorten the question and search again.",
    "invalid_corpus": "Check the approved corpus manifest before searching again.",
    "retrieval_failed": "The document index could not be searched. Check the active corpus setup.",
    "model_unavailable": "Start Ollama and verify that the configured local model is available.",
    "model_timeout": "The local answer model took too long to reply. Try the question again.",
}


@st.cache_resource(show_spinner=False)
def encoder_resource() -> tuple[Encoder, Lock]:
    return Encoder(), Lock()


def render_import(manifest_path: Path, approved_count: int, index_dir: Path) -> None:
    with st.sidebar.expander("Import approved documents"):
        if not approved_count:
            st.info("Configure an approved manifest before importing documents.")
            return
        with st.form("corpus-import"):
            uploads = st.file_uploader(
                "Approved PDF or TXT files", type=["pdf", "txt"], accept_multiple_files=True
            )
            version = st.text_input("New corpus version", max_chars=64, placeholder="corpus-v2")
            submitted = st.form_submit_button("Build index")
        if not submitted:
            return

        names = [upload.name for upload in uploads]
        if len(names) != len(set(names)):
            st.error("Upload only one copy of each filename.")
            return
        try:
            chunks, flagged = prepare_import(
                {upload.name: upload.getbuffer() for upload in uploads},
                manifest_path,
                index_dir,
                version.strip(),
            )
        except ValueError as exc:
            st.error("The approved files could not be imported.")
            render_literal(str(exc))
            return
        except OSError:
            st.error("The approved files could not be read. Check local file permissions.")
            return
        try:
            with st.spinner("Building the index…"):
                encoder, lock = encoder_resource()
                with lock:
                    metadata = build_index(chunks, encoder, index_dir, version.strip())
        except Exception:  # noqa: BLE001 - the encoder and database raise backend-specific errors.
            st.error("The index could not be built. Check your local model and index settings.")
            return
        st.session_state["built_corpus"] = (metadata["corpus_version"], len(uploads), flagged)
        st.rerun()


def render_literal(value: str) -> None:
    st.html(f'<p style="white-space: pre-wrap; overflow-wrap: anywhere">{escape(value)}</p>')


def markdown_literal(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", escape(value)).replace("\n", " ")


def render_response(response: AnswerResponse) -> None:
    if response.status == "error":
        st.error(ERROR_MESSAGES.get(response.reason, "The search could not finish. Try again."))
        st.caption(f"Request ID `{response.request_id}`")
        return
    st.subheader("Answer")
    if response.status == "no_answer":
        st.info(response.answer)
        return

    render_literal(response.answer)
    st.subheader("Sources")
    for citation in response.citations:
        title = markdown_literal(citation.document_title)
        with st.expander(f"{title} · {citation.location}"):
            st.caption(
                f"{markdown_literal(citation.document_id)} · "
                f"version {markdown_literal(citation.document_version)}"
            )
            render_literal(citation.supporting_excerpt)
            if not citation.source_url:
                continue
            try:
                source = urlsplit(citation.source_url)
            except ValueError:
                continue
            if source.scheme == "https" and source.hostname and source.username is None:
                st.link_button("Open source document", citation.source_url)


def request_answer(
    question: str,
    index_dir: Path,
    version: str,
    manifest_path: Path,
    model_name: str,
    settings: tuple[int, float],
) -> AnswerResponse:
    from rag_assistant.generation import OllamaModel
    from rag_assistant.pipeline import AnswerPipeline

    top_k, max_distance = settings
    encoder, lock = encoder_resource()
    with lock:
        return AnswerPipeline(
            index_dir,
            version,
            manifest_path,
            encoder,
            OllamaModel(model_name),
            max_distance=max_distance,
            top_k=top_k,
        ).answer(question)


def main() -> None:
    st.set_page_config(page_title="Medical Document Assistant", layout="centered")
    st.title("Medical Document Assistant")
    st.warning(PROTOTYPE_NOTICE)
    st.caption(
        "Search approved reference documents. Use general questions without patient details."
    )

    manifest_path = Path(os.environ.get("RAG_MANIFEST", "data/manifest.jsonl"))
    index_dir = Path(os.environ.get("RAG_INDEX_DIR", "data/index"))
    calibration = Path(
        os.environ.get("RAG_CALIBRATION", "data/evaluation-results/calibration.json")
    )
    model_name = os.environ.get("RAG_OLLAMA_MODEL", "").strip()

    try:
        approved_count = len(load_manifest(manifest_path))
        manifest_revision = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
        approved_count, manifest_revision = 0, None

    st.sidebar.header("Approved corpus")
    st.sidebar.caption(f"{approved_count} documents in the approved manifest")
    versions = available_versions(index_dir)
    configured_version = os.environ.get("RAG_CORPUS_VERSION", "")
    if built := st.session_state.pop("built_corpus", None):
        st.session_state["active_corpus"] = built[0]
        st.sidebar.success(f"Indexed {built[1]} document(s) in {built[0]}.")
        if built[2]:
            st.sidebar.warning(f"{built[2]} page(s) had no usable text. Review the source files.")

    if versions:
        if "active_corpus" not in st.session_state and configured_version in versions:
            st.session_state["active_corpus"] = configured_version
        version = st.sidebar.selectbox(
            "Corpus version",
            options=sorted(versions),
            index=None,
            placeholder="Select a built index",
            key="active_corpus",
        )
    else:
        st.sidebar.info("No local corpus index is available.")
        version = None

    render_import(manifest_path, approved_count, index_dir)

    settings = None
    if not approved_count:
        st.info("Add an approved corpus manifest to use document search.")
    elif version is None:
        st.info("Build or select an approved corpus index to use document search.")
    else:
        try:
            settings = retrieval_settings(calibration, versions[version])
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, OverflowError):
            st.info("Set up development-set calibration for this corpus version before searching.")
        if not model_name:
            st.info("Configure the approved local Ollama model before searching.")

    current_context = (version, manifest_revision, settings, model_name)
    if st.session_state.get("answer_context") != current_context:
        st.session_state.pop("last_answer", None)
        st.session_state["answer_context"] = current_context

    ready = bool(approved_count and version and settings and model_name)
    with st.form("document-question"):
        question = st.text_area(
            "Question", height=100, max_chars=MAX_QUESTION_LENGTH, disabled=not ready
        )
        submitted = st.form_submit_button("Search documents", type="primary", disabled=not ready)

    if submitted:
        st.session_state.pop("last_answer", None)
        if not question.strip():
            st.warning("Enter a question to search the documents.")
        else:
            try:
                with st.spinner("Searching the approved documents…"):
                    st.session_state["last_answer"] = request_answer(
                        question.strip(), index_dir, version, manifest_path, model_name, settings
                    )
            except Exception:  # noqa: BLE001 - startup may fail before a response can be created.
                st.error("The search could not start. Check the local index and model setup.")

    if response := st.session_state.get("last_answer"):
        render_response(response)


if __name__ == "__main__":
    main()
