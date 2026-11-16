"""
Run RAG evaluation on the curated dataset.

Chalta hai:
    python tests\\run_evaluation.py

Options:
    --no-judge          LLM judge skip karo (fast)
    --limit N           Sirf pehle N items
    --save-baseline     Current run ko baseline ke tor par save karo
    --compare           Baseline se compare karo
    --delay N           Har query ke beech delay (rate limit ke liye)

Output:
    - Console report
    - tests/eval_reports/eval-YYYYMMDD-HHMMSS.json
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.rag_pipeline import RAGPipeline
from app.services.llm import generate
from app.services.evaluator import (
    EvalItemResult,
    compute_hit_and_mrr,
    compute_answer_correct,
    compute_source_correct,
    judge_faithfulness,
    aggregate,
    format_report,
    summary_to_dict,
    item_to_dict,
)


DATASET_PATH = Path(__file__).parent / "eval_dataset.json"
REPORTS_DIR = Path(__file__).parent / "eval_reports"
BASELINE_PATH = REPORTS_DIR / "baseline.json"


def load_dataset(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_one(pipe: RAGPipeline, item: dict, use_judge: bool) -> EvalItemResult:
    """Ek item evaluate karo."""
    result = EvalItemResult(
        item_id=item["id"],
        category=item.get("category", "unknown"),
        question=item["question"],
        should_be_not_found=item.get("should_be_not_found", False),
    )

    t0 = time.time()
    ra = pipe.ask(item["question"], top_k=8)
    result.elapsed = time.time() - t0

    result.answer = ra.answer
    result.found_in_documents = ra.found_in_documents

    # Retrieved pages (from used_sources)
    result.retrieved_pages = sorted({
        g["page_number"] for g in ra.used_sources
    })

    # Out-of-scope handling
    if result.should_be_not_found:
        result.not_found_correct = not ra.found_in_documents
        result.answer_correct = not ra.found_in_documents
        return result

    # In-scope metrics
    expected_pages = item.get("expected_pages", [])
    expected_kw = item.get("expected_answer_keywords", [])
    match_mode = item.get("match_mode", "all")

    # Retrieval
    hit, rr = compute_hit_and_mrr(result.retrieved_pages, expected_pages)
    result.hit = hit
    result.reciprocal_rank = rr

    # Answer (with match_mode)
    correct, missing = compute_answer_correct(
        ra.answer, expected_kw, match_mode=match_mode
    )
    result.answer_correct = correct
    result.missing_keywords = missing

    # Source
    result.source_pages = result.retrieved_pages
    result.source_correct = compute_source_correct(
        result.source_pages, expected_pages
    )

    # Faithfulness (LLM judge)
    if use_judge:
        context = "\n\n".join(
            h.text for h in ra.retrieved_chunks[:5]
        )
        score, reason = judge_faithfulness(ra.answer, context, generate)
        result.faithfulness_score = score
        result.faithfulness_reason = reason

    return result


def save_report(summary, results, tag: str = "") -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"eval-{ts}{('-' + tag) if tag else ''}.json"
    path = REPORTS_DIR / fname

    payload = {
        "timestamp": ts,
        "tag": tag,
        "summary": summary_to_dict(summary),
        "items": [item_to_dict(r) for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def save_baseline(summary, results) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "summary": summary_to_dict(summary),
        "items": [item_to_dict(r) for r in results],
    }
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return BASELINE_PATH


def compare_with_baseline(summary) -> None:
    if not BASELINE_PATH.exists():
        print("  [compare] Baseline mojood nahi. Pehle --save-baseline chalao.")
        return
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        base = json.load(f)

    curr = summary_to_dict(summary)
    base_s = base["summary"]

    print()
    print("  --- Baseline Comparison ---")
    print(f"  {'Metric':<25s}  {'Baseline':>10s}  {'Current':>10s}  {'Delta':>10s}")
    print(f"  {'-'*25}  {'-'*10}  {'-'*10}  {'-'*10}")

    keys = [
        ("hit_rate", "Hit Rate"),
        ("mrr", "MRR"),
        ("answer_correct_rate", "Answer Correctness"),
        ("source_correct_rate", "Source Correctness"),
        ("faithfulness_avg", "Faithfulness"),
        ("not_found_accuracy", "Not-Found Acc."),
        ("avg_elapsed", "Avg Time (s)"),
    ]
    for key, label in keys:
        b = base_s.get(key)
        c = curr.get(key)
        if b is None and c is None:
            continue
        if b is None or c is None:
            print(f"  {label:<25s}  {str(b):>10s}  {str(c):>10s}  {'-':>10s}")
            continue
        delta = c - b
        sign = "+" if delta > 0 else ""
        if key == "avg_elapsed":
            arrow = "↓" if delta < 0 else ("↑" if delta > 0 else "=")
        else:
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  {label:<25s}  {b:>10.3f}  {c:>10.3f}  {sign}{delta:>9.3f} {arrow}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG Evaluation")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM judge")
    parser.add_argument("--limit", type=int, default=None, help="Max items")
    parser.add_argument("--save-baseline", action="store_true",
                        help="Save as baseline")
    parser.add_argument("--compare", action="store_true",
                        help="Compare with baseline")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between queries (rate limit)")
    args = parser.parse_args()

    data = load_dataset(DATASET_PATH)
    items = data["items"]
    if args.limit:
        items = items[: args.limit]

    print()
    print("=" * 70)
    print("  RAG EVALUATION")
    print("=" * 70)
    print(f"  Dataset:     {DATASET_PATH}")
    print(f"  Total items: {len(items)}")
    print(f"  LLM judge:   {'OFF' if args.no_judge else 'ON'}")
    print(f"  Delay:       {args.delay}s between queries")
    print()

    pipe = RAGPipeline.load()
    if pipe.store.is_empty:
        print("  Store khaali hai. Pehle ingest karo.")
        return 1

    results = []
    use_judge = not args.no_judge

    for i, item in enumerate(items, 1):
        q = item["question"]
        print(f"  [{i:2d}/{len(items)}] {q[:60]}")
        try:
            res = evaluate_one(pipe, item, use_judge)
            results.append(res)
            status = "OK" if res.answer_correct else "MISS"
            print(f"           → {status}  (found={res.found_in_documents}, "
                  f"pages={res.retrieved_pages[:3]}, {res.elapsed:.1f}s)")
        except Exception as e:
            print(f"           → ERROR: {type(e).__name__}: {e}")

        # Rate limit guard
        if i < len(items) and args.delay > 0:
            time.sleep(args.delay)

    if not results:
        print("  Koi result nahi. Abort.")
        return 1

    # Aggregate + report
    summary = aggregate(results)
    report = format_report(summary, results)
    print()
    print(report)

    # Save report
    tag = "judge" if use_judge else "no-judge"
    path = save_report(summary, results, tag=tag)
    print(f"  Report saved: {path}")

    if args.save_baseline:
        bpath = save_baseline(summary, results)
        print(f"  Baseline saved: {bpath}")

    if args.compare:
        compare_with_baseline(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())