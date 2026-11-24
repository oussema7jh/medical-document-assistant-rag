"""Score a RAG system against the evaluation dataset (see data/eval/rubric.md).

Predictions file: JSONL, one record per question:
  {"question_id": "T-001", "refused": false, "answer": "...",
   "cited_document_id": "DOC-03", "cited_page": 1,
   "supported": 1}            # supported = 0/1 human (or calibrated judge) label, answerable questions only

Usage: python scripts/score_eval.py --split test --pred runs/run1.jsonl
"""

import argparse
import json

TARGETS = {"source_correct": 0.90, "answer_supported": 0.90, "correct_refusal": 0.85}


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def source_ok(gold, pred, tol=0):
    if pred.get("refused") or not pred.get("cited_document_id"):
        return False
    options = [(gold["document_id"], gold["page"])] + [
        (s["document_id"], s["page"]) for s in gold["alt_sources"]
    ]
    return any(
        pred["cited_document_id"] == d and abs((pred.get("cited_page") or -99) - p) <= tol
        for d, p in options
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--pred", required=True)
    ap.add_argument("--dir", default="data/eval")
    a = ap.parse_args()
    gold = {r["question_id"]: r for r in load(f"{a.dir}/{a.split}.jsonl")}
    preds = {r["question_id"]: r for r in load(a.pred)}
    missing = [q for q in gold if q not in preds]
    if missing:
        raise SystemExit(f"missing predictions for: {missing}")

    ans = [q for q, g in gold.items() if g["answerable"]]
    noa = [q for q, g in gold.items() if not g["answerable"]]
    res = {
        "n_answerable": len(ans),
        "n_no_answer": len(noa),
        "source_correct": sum(source_ok(gold[q], preds[q]) for q in ans) / len(ans),
        "source_correct_lenient_pm1": sum(source_ok(gold[q], preds[q], 1) for q in ans) / len(ans),
        "answer_supported": sum(
            1 for q in ans if not preds[q].get("refused") and preds[q].get("supported") == 1
        )
        / len(ans),
        "false_refusal_rate": sum(bool(preds[q].get("refused")) for q in ans) / len(ans),
        "correct_refusal": sum(bool(preds[q].get("refused")) for q in noa) / len(noa),
    }
    res["unlabelled_supported"] = sum(
        1 for q in ans if not preds[q].get("refused") and "supported" not in preds[q]
    )
    for k, t in TARGETS.items():
        res[f"{k}_meets_target"] = res[k] >= t
    print(json.dumps(res, indent=2))
    print("\nFailures:")
    for q in ans:
        if not source_ok(gold[q], preds[q]):
            print(f"  {q} source wrong/refused ({gold[q]['document_id']} p.{gold[q]['page']})")
    for q in noa:
        if not preds[q].get("refused"):
            print(f"  {q} answered a no-answer question ({gold[q]['no_answer_type']})")


if __name__ == "__main__":
    main()
