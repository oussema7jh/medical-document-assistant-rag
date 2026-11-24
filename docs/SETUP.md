# Retrieval prototype setup

This is a local academic prototype. **Prototype — not for medical use.** It cannot answer questions until a corpus is approved and built. Raw documents and indexes stay outside Git.

1. Install Python 3.11 and [uv](https://docs.astral.sh/uv/).
2. Run `uv sync --locked --extra dev` from the repository root.
3. Review `docs/CORPUS_CANDIDATES.md`. The candidate downloader is `uv run python scripts/download_candidate_corpus.py`; it stores public PDFs in ignored `data/raw/` and writes a candidate manifest. Check each source, edition, page count, extraction quality and permitted use. Change `approval_status` to `approved` only after actual course/supervisor approval; copy the reviewed manifest to ignored `data/manifest.jsonl`.
4. Run `uv run python -m rag_assistant.cli ingest data/manifest.jsonl data/raw data/extracted/pages.jsonl`. Inspect errors and every flagged page. Do not build when missing pages undermine the corpus.
5. Run `uv run python -m rag_assistant.cli build data/extracted/pages.jsonl data/index corpus-v1`. The first run downloads the pinned multilingual E5 model. A version name cannot be rebuilt in place; use a new corpus version to preserve the last index.
6. Before final evaluation, create a separate development JSONL with `id`, `question`, `answerable`, `document_id`, `location`, and `split: "development"`. Run `uv run python scripts/calibrate_retrieval.py data/development.jsonl data/index corpus-v1 data/evaluation-results/calibration.json`. Review the report and freeze its top-k and distance threshold. A cosine distance is not a medical confidence score.
7. Run queries with `uv run python -m rag_assistant.cli query data/index corpus-v1 "question" --top-k 5 --max-distance <calibrated-value>`.
8. Only after freezing the corpus, index and configuration, run `uv run python scripts/evaluate_retrieval.py data/final-questions.jsonl data/index corpus-v1 data/evaluation-results/final.csv --top-k <frozen-k> --max-distance <frozen-value>`. Final questions require `split: "final"` and the planned 45 answerable / 15 absent mix. The script writes raw CSV and a summary JSON. Its source metric is **retrieval recall**, not generated citation accuracy. Human reviewers must score answer citations and grounding separately.

Run `uv run pytest -q` and `uv run ruff check .` before opening a pull request. The local model and Chroma data may require significant disk space. Do not place patient data or secrets in the corpus.

## Launch the question interface

Install the locked environment, start local Ollama in local-only mode (`OLLAMA_NO_CLOUD=1`),
and make the supervisor-approved instruction model available in its local inventory. Set
`RAG_OLLAMA_MODEL` to that exact model name and tag. Then run from the repository root.

```console
uv run --locked streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://127.0.0.1:8501`).
Configure these environment variables before launch if the defaults differ from your setup.

| Variable | Default | Purpose |
|---|---|---|
| `RAG_OLLAMA_MODEL` | Required | Exact local model name and tag approved for the project. |
| `RAG_MANIFEST` | `data/manifest.jsonl` | Approved JSONL manifest. |
| `RAG_INDEX_DIR` | `data/index` | Directory with the built Chroma indexes. |
| `RAG_CORPUS_VERSION` | Choose in the sidebar | Corpus version selected at launch. |
| `RAG_CALIBRATION` | `data/evaluation-results/calibration.json` | Development calibration report for the selected corpus version. |

The sidebar can build a new index from a selection of already approved PDF/TXT files.
Every upload must match a filename and SHA-256 in the configured manifest. For a full
corpus build, select the full approved set. Review any unreadable pages reported after import.
Use the development calibration command above to generate a report for the new version
before searching it. The prototype listens on the local machine by default.
