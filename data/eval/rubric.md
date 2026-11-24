# Scoring rubric: Medical Document Assistant (RAG)

Dataset version: **v1.0**. Applies to `data/eval/test.jsonl` (final, held-out) and `data/eval/dev.jsonl` (development).
Questions and expected answers are in French, the language of the corpus. Run one system configuration per run and score every question.

## 1. Metrics and targets

| Metric | Computed on | Definition | Target |
|---|---|---|---|
| **Source correct** | 45 answerable | The answer cites the gold `document_id` **and** the gold `page` (or one of its `alt_sources`). Exact page match. | ≥ 90 % |
| **Answer supported** | 45 answerable | Manual label 1 (see §2), and the system did not refuse. | ≥ 90 % |
| **Correct refusal** | 15 no-answer | The system declines (§3) and gives no substantive clinical claim. | ≥ 85 % |
| False refusal rate | 45 answerable | Share of answerable questions the system wrongly refused. Report only; it is the cost of a strict threshold. | n/a |
| Source correct, lenient | 45 answerable | Same as source correct but a cited page within ±1 counts. Report only. | n/a |

A refusal on an answerable question counts as source incorrect and answer not supported. Answering a no-answer question counts as an incorrect refusal.

## 2. Answer supported (human label, 0/1)

Label **1** only if all of the following hold:
1. Every claim in the answer is stated by the cited passage (nothing invented, nothing from general knowledge).
2. Every key fact in `expected_answer` is present: numbers (doses, durations, thresholds, ages) match **exactly**, and units and frequencies are right.
3. Nothing in the answer contradicts the corpus.

Label **0** if a key number is wrong or missing, an unsupported claim is added, or the answer is correct but not backed by the cited passage. Extra correct detail from the same passage is allowed. For list answers, every item in `expected_answer` must be present.

Calibration: two people label the same 10 test answers before the final run, then compare. If an LLM judge is used, report its agreement with these human labels.

## 3. What counts as a refusal

The answer says, in any wording, that the information is not in the documents (reference wording: *« Je n'ai pas pu trouver cette information dans les documents. »*) and does not state a dose, duration, threshold or recommendation. Hedged answers such as "not found, but typically…" fail.

## 4. Source rules
- `page` is the PDF page index, which equals the printed footer number in all six documents (DOC-01 page 1 is unnumbered).
- Some answers appear in two places (see `alt_sources`); either counts.
- Questions that differ between the adult and the child angina fiches name the population (adulte/enfant). Citing the wrong population's fiche is source incorrect.
- DOC-05 stakeholder comments marked "Non pris en compte" were not adopted; no question depends on them.

## 5. Dev / test protocol
1. Tune thresholds, chunk size, top-k and prompts **only** on `dev.jsonl`.
2. `test.jsonl` is frozen at `v1.0` once Oussema signs off. Do not read test failures to change the system.
3. Run the final configuration on the test set once and report those numbers.
4. Any change to a test question (wording, answer or page) requires a new dataset version (`v1.1`), a CHANGELOG entry and a re-run of all systems being compared.
5. `dev` and `test` share no question and no passage-answer pair (checked by `scripts/validate_eval.py`).

## 6. Review checklist (Oussema)
For each question in `test.csv` (status `draft_pending_review` becomes `reviewed`, `reviewed_by` filled):
- [ ] Opening the cited document at the cited page, the expected answer is stated there.
- [ ] Numbers, units and frequencies in the expected answer are exact.
- [ ] The question has a single defensible answer and names the population when needed.
- [ ] For no-answer rows: a keyword search across **all** corpus PDFs finds no passage that answers it. Search terms are listed in `notes`.
