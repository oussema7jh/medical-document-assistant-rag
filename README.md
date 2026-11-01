# Medical Document Assistant Using RAG

Doctoline academic Project 05. **Prototype — not for medical use.**

## Goal
Answer staff questions using only an approved corpus of 20–30 public or approved documents. Return short answers with document/page citations and abstain when the evidence is absent.

## Team
- **Oussema Braham**: ingestion, indexing, retrieval, code review and final integration. Reviews Lina's PRs and performs merges after validation.
- **Lina**: evaluation questions, generation, citations, interface, user guide and presentation. Opens PRs and resolves review feedback; peer-reviews Oussema's changes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow. Automated branch protection is not configured.

## Schedule
Project start: **2 November 2026**. Final delivery: **13 December 2026**. Official presentation time is to be confirmed.

| Sprint | Start | Deadline | Outcome |
|---|---|---|---|
| 1 | 2 Nov | 8 Nov | Scope, approved corpus and evaluation questions |
| 2 | 9 Nov | 15 Nov | Extraction, metadata, response schema and UI design |
| 3 | 16 Nov | 22 Nov | Index, grounded generation and citations |
| 4 | 23 Nov | 29 Nov | Complete MVP and abstention |
| 5 | 30 Nov | 6 Dec | Evaluation and error analysis |
| 6 | 7 Dec | 13 Dec | Integration, documentation and presentation |

[ClickUp task plan](https://app.clickup.com/1200490000005648/v/l/li/1200490000038008)

## Planned implementation
Python, per-page PDF/TXT extraction, sentence-transformer embeddings, FAISS or Chroma, an approved language model and a Streamlit interface. The initial repository contains planning and collaboration documents; the prototype is not implemented yet.

## Evaluation targets
60 questions, including 15 without answers in the corpus. Target >=90% correct sources, >=90% supported answers and >=85% correct abstention. Report raw counts and denominators; keep tuning examples separate from final evaluation. These are targets, not achieved results.

## Data restrictions
No real patient data, no real Doctoline integration and no clinical decisions. Use approved/public reference documents and fictional patient examples. Never commit secrets or raw local data.

## Final deliverables
Working prototype, reproducible source/setup instructions, evaluation and limitations, technical report, user guide and final demonstration.
