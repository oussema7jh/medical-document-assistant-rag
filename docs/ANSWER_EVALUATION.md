# Answer evaluation

Use the 60 held-out questions only after Oussema reviews the expected answers and absent cases and the team freezes the approved corpus, index, local model and development-calibrated settings. Complete the run against that single configuration. Keep raw outputs for any later rerun under a new filename.

## Run

Provide final JSONL with `id`, `question`, `split: "final"`, `answerable`, `document_id` and `location`. For an answerable case use the exact `page N` or `lines N-M` from the approved corpus. Supply `document_version` when available. Add other valid source records under `alternative_sources`. For absent cases leave the expected source empty. Keep tuning examples outside this file.

```bash
uv run python scripts/evaluate_answers.py run data/final-questions.jsonl data/manifest.jsonl data/index corpus-v1 data/evaluation-results/answers-v1.json --model approved-model:tag --top-k 5 --max-distance 0.3
```

The model name, top-k and distance above illustrate the syntax. Replace them with the frozen approved values. Record the local model digest alongside the run. The output records the file hashes, configuration, request status, raw answer, validated citations, retrieved and prompted chunk IDs, and timings.

## Review and score

For every answered case, split the answer into claims and verify each claim and qualifier against the cited excerpt and original source. Mark it supported only if the answer addresses the question and every material claim has evidence. Record omitted required details as `partial_answer` and unsupported or contradictory claims as `unsupported_claim`. For ambiguous cases compare ratings with Oussema and record the resolution. Inspect answerable refusals and errors separately. Review the rejected citations recorded under `invalid_citation`.

Create a review JSONL with one row per answered case, with `id`, `reviewer`, boolean `supported`, optional `issue` and `note`, and `run_sha256` for the exact raw output reviewed. Use `Get-FileHash` on PowerShell or `sha256sum` on Linux to compute that hash.

```bash
uv run python scripts/evaluate_answers.py score data/final-questions.jsonl data/evaluation-results/answers-v1.json data/evaluation-results/score-v1.json --reviews data/evaluation-results/reviews-v1.jsonl
```

Report supported answers over all generated answers (90% target) and include the number answered out of 45 answerable questions. For the 15 absent questions, report actual no-answer responses over 15 (85% target, at least 13/15). Errors stay in the denominator and do not count as correct refusals. Source accuracy counts the answerable cases whose response includes an expected document and exact location over 45. The score includes counts of partial answers, invented citations, unnecessary refusals and errors. Grounding remains unset until every generated answer has a human label.

## Results

The approved corpus, frozen settings and cross-reviewed run are pending. Unit tests use synthetic records to check the scoring rules. Report measured values here once the approved run and peer cross-check are complete.
