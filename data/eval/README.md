# Evaluation dataset

**Draft pending corpus alignment and peer review.** This branch preserves Lyna's HAS-based
question draft. Its six PDF checksums do not match any of the 20 CDC candidate files in
`data/candidate-manifest.jsonl`. Confirm the approved corpus with Oussema and the supervisor
before selecting or revising these questions for the final evaluation. Recheck both the
answerable and no-answer cases whenever the corpus changes.

| File | Purpose |
|---|---|
| `test.jsonl` / `test.csv` | **Held-out draft**: 45 answerable + 15 no-answer (`T-001`…`T-060`) |
| `dev.jsonl` / `dev.csv` | **Development set** for threshold tuning: 14 answerable + 6 no-answer (`D-001`…`D-020`) |
| `corpus_manifest.json` | Corpus index: `document_id`, title, printed version, page count, file name, SHA-256 |
| `rubric.md` | Scoring rubric and review checklist |

## Record schema
`question_id`, `split`, `question`, `expected_answer`, `answerable`, `document_id`, `document_version`, `page`, `alt_sources` (other valid `{document_id, page}`), `question_type` (`numeric`, `list`, `rule`, `definition`, `factual`, `no_answer`), `no_answer_type` (`near_miss`, `related_gap`, `out_of_scope`), `notes`, `status`, `reviewed_by`, `dataset_version`.
No-answer rows have `answerable: false` and null `document_id`, `document_version` and `page`.

## Corpus
| ID | Document | Version |
|---|---|---|
| DOC-01 | HTA essentielle de l'adulte, synthèse | reco. 2005, synthèse 2007 |
| DOC-02 | Parcours de soins DT2 | juin 2025 |
| DOC-03 | Angine aiguë de l'enfant | juillet 2021, MAJ mai 2025 |
| DOC-04 | Douleur de l'enfant : alternatives à la codéine | janvier 2016 |
| DOC-05 | Durées d'antibiothérapies, volet 1 (rapport) | juillet 2021, MAJ mai 2025 |
| DOC-06 | Angine aiguë de l'adulte | nov. 2016, MAJ juillet 2021 et 2024 |

Two uploaded files are exact duplicates (DOC-02 and DOC-03 each appear twice); keep one copy of each in the corpus.

## Known cases the dataset tests on purpose
- **Adult vs child** angina fiches have similar wording and different doses (T-001…T-003 vs T-030…T-032, no-answer T-046, T-053).
- **Cross-document overlap** (paracetamol/ibuprofen doses in DOC-03 and DOC-04): handled with `alt_sources`.
- **Conflicting targets**: diabetic blood-pressure target is < 130/80 in DOC-01 but PA < 140/85 appears in DOC-02 p.43 (retinopathy). T-015 names the HTA synthesis.
- **Document age**: DOC-01 (2005/2007) and DOC-04 (2016) are old and unrevised; DOC-05 explicitly keeps the 2016 angina recommendations in force. The final report should mention that guideline age varies by domain.

## Structural and source checks

Run the structural check whenever either data format changes. With the six exact HAS files
available, run the PDF check to verify file hashes, page counts, and readability of every
cited page. Oussema's separate review covers whether the citations support the expected answers
and whether each no-answer case is absent from the entire selected corpus.

```bash
uv run python scripts/validate_eval.py
uv run python scripts/check_against_pdfs.py --pdf-dir path/to/pdfs
```

## Retrieval evaluator input

Use the exact approved manifest supplied for the indexed corpus. The exporter compares the
complete document ID set, versions, and SHA-256 hashes and creates a separate file for each
split. The export includes expected answers for human review and versioned primary and
alternative citations for generated answer scoring. The retrieval-only evaluator measures
primary document and page retrieval.

```bash
uv run python scripts/validate_eval.py --approved-manifest data/manifest.jsonl --split dev --export data/development.jsonl
uv run python scripts/validate_eval.py --approved-manifest data/manifest.jsonl --split test --export data/final-questions.jsonl
```

Use the development export for tuning. After Oussema verifies each final item, record the
review in both formats. Freeze the corpus, development-selected configuration and final
dataset version before exporting and running the final set. An unreviewed final export fails.

## Versioning
`dataset_version` is in every record and in the manifest. After review: `git tag eval-v1.0`. Test-set changes follow rubric §5.
