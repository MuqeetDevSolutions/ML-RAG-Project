"""
RAG Evaluator — metrics calculation.

Metrics:
    1. Retrieval Hit Rate    — kya expected page top-K me aaya?
    2. Retrieval MRR         — Mean Reciprocal Rank
    3. Answer Correctness    — keywords matched?
    4. Source Correctness    — kya expected page sources me hai?
    5. Faithfulness          — LLM judge: kya answer context me support hai?
    6. Hallucination Rate    — out-of-scope par galat answer?

Yeh module **metrics computation** karta hai. Actual run
`tests/run_evaluation.py` me hai.

Design:
    - Pure functions — metrics calculation
    - LLM judge ek optional feature (0/1 score deta hai)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import re

from app.services.rag_pipeline import RAGAnswer


# ================================================================
# Per-item result
# ================================================================

@dataclass
class EvalItemResult:
    """Ek item ka evaluation result."""
    item_id: str
    category: str
    question: str

    # Retrieval
    hit: bool = False
    reciprocal_rank: float = 0.0
    retrieved_pages: List[int] = field(default_factory=list)

    # Answer
    answer: str = ""
    answer_correct: bool = False
    missing_keywords: List[str] = field(default_factory=list)

    # Sources
    source_correct: bool = False
    source_pages: List[int] = field(default_factory=list)

    # Found / not found
    found_in_documents: bool = True
    should_be_not_found: bool = False
    not_found_correct: bool = True

    # Faithfulness (optional — LLM judge)
    faithfulness_score: Optional[float] = None
    faithfulness_reason: str = ""

    # Timing
    elapsed: float = 0.0


# ================================================================
# Retrieval metrics
# ================================================================

def compute_hit_and_mrr(
    retrieved_pages: List[int],
    expected_pages: List[int],
) -> tuple[bool, float]:
    """
    Hit = kya koi bhi expected page top-K me hai?
    MRR = 1 / (rank of first match)

    Returns:
        (hit, reciprocal_rank)
    """
    if not expected_pages or not retrieved_pages:
        return False, 0.0

    expected_set = set(expected_pages)
    for i, page in enumerate(retrieved_pages, start=1):
        if page in expected_set:
            return True, 1.0 / i
    return False, 0.0


# ================================================================
# Answer metrics
# ================================================================

def compute_answer_correct(
    answer: str,
    expected_keywords: List[str],
    match_mode: str = "all",
) -> tuple[bool, List[str]]:
    """
    Answer sahi hai agar keywords match karein.

    Args:
        answer: LLM ka jawab
        expected_keywords: keywords to look for
        match_mode: "all" (sab chahiye) ya "any" (koi ek kaafi)

    Returns:
        (is_correct, missing_keywords)
    """
    if not expected_keywords:
        return True, []

    answer_lower = answer.lower()
    missing = [kw for kw in expected_keywords if kw.lower() not in answer_lower]

    if match_mode == "any":
        # Agar kam se kam ek keyword mila
        matched_any = len(missing) < len(expected_keywords)
        return matched_any, missing
    else:
        # "all" — saare keywords chahiye
        return len(missing) == 0, missing


# ================================================================
# Source metrics
# ================================================================

def compute_source_correct(
    source_pages: List[int],
    expected_pages: List[int],
) -> bool:
    """Kya expected page sources me hai?"""
    if not expected_pages:
        return True
    return bool(set(source_pages) & set(expected_pages))


# ================================================================
# LLM judge (faithfulness)
# ================================================================

FAITHFULNESS_PROMPT = """You are a strict fact-checking judge for RAG systems.

Task: Determine whether the ANSWER is fully supported by the CONTEXT.

RULES:
1. Read the CONTEXT carefully.
2. Read the ANSWER.
3. If every factual claim in the ANSWER can be traced back to the CONTEXT,
   the answer is FAITHFUL.
4. If the ANSWER contains any fact NOT in the CONTEXT (even if true in reality),
   the answer is UNFAITHFUL.
5. If the answer says "I could not find this information..." and the context
   truly lacks the answer, that's FAITHFUL (score 1).
6. If the answer says "I could not find..." but the context DOES contain the
   answer, that's UNFAITHFUL (score 0).

Output ONLY a single number:
    1  (if faithful)
    0  (if unfaithful)
"""


def judge_faithfulness(
    answer: str,
    context: str,
    llm_generate_fn,
) -> tuple[float, str]:
    """
    LLM se faithfulness judge karo.

    Returns:
        (score, reason)  score: 0.0 ya 1.0
    """
    prompt = (
        f"CONTEXT:\n{context[:4000]}\n\n"
        f"ANSWER:\n{answer[:1500]}\n\n"
        f"Output only 1 or 0:"
    )
    try:
        out = llm_generate_fn(
            prompt=prompt,
            system=FAITHFULNESS_PROMPT,
            temperature=0.0,
            max_tokens=10,
        )
        out = (out or "").strip()
        match = re.search(r"[01]", out)
        score = float(match.group()) if match else 1.0
        return score, out[:60]
    except Exception as e:
        return 1.0, f"[judge error: {type(e).__name__}]"


# ================================================================
# Aggregate metrics
# ================================================================

@dataclass
class EvalSummary:
    """Poore evaluation ka summary."""
    total: int = 0
    in_scope_total: int = 0
    out_of_scope_total: int = 0

    hit_rate: float = 0.0
    mrr: float = 0.0
    answer_correct_rate: float = 0.0
    source_correct_rate: float = 0.0

    faithfulness_avg: Optional[float] = None
    faithfulness_count: int = 0

    not_found_accuracy: float = 0.0
    avg_elapsed: float = 0.0

    per_category: Dict[str, Dict[str, float]] = field(default_factory=dict)


def aggregate(results: List[EvalItemResult]) -> EvalSummary:
    """Per-item results se aggregate metrics nikalo."""
    summary = EvalSummary()
    summary.total = len(results)
    if summary.total == 0:
        return summary

    in_scope = [r for r in results if not r.should_be_not_found]
    out_scope = [r for r in results if r.should_be_not_found]
    summary.in_scope_total = len(in_scope)
    summary.out_of_scope_total = len(out_scope)

    if in_scope:
        summary.hit_rate = sum(1 for r in in_scope if r.hit) / len(in_scope)
        summary.mrr = sum(r.reciprocal_rank for r in in_scope) / len(in_scope)
        summary.answer_correct_rate = sum(
            1 for r in in_scope if r.answer_correct
        ) / len(in_scope)
        summary.source_correct_rate = sum(
            1 for r in in_scope if r.source_correct
        ) / len(in_scope)

    correct_not_found = sum(1 for r in out_scope if r.not_found_correct)
    false_negatives = sum(1 for r in in_scope if not r.found_in_documents)
    summary.not_found_accuracy = (
        (correct_not_found + (len(in_scope) - false_negatives))
        / max(1, len(results))
    )

    faith_vals = [
        r.faithfulness_score for r in results
        if r.faithfulness_score is not None
    ]
    if faith_vals:
        summary.faithfulness_avg = sum(faith_vals) / len(faith_vals)
        summary.faithfulness_count = len(faith_vals)

    summary.avg_elapsed = sum(r.elapsed for r in results) / len(results)

    categories = {}
    for r in results:
        cat = r.category or "unknown"
        if cat not in categories:
            categories[cat] = {"count": 0, "answer_correct": 0, "hit": 0}
        categories[cat]["count"] += 1
        if r.answer_correct:
            categories[cat]["answer_correct"] += 1
        if r.hit:
            categories[cat]["hit"] += 1
    for cat, stats in categories.items():
        c = max(1, stats["count"])
        summary.per_category[cat] = {
            "count": stats["count"],
            "answer_correct_rate": stats["answer_correct"] / c,
            "hit_rate": stats["hit"] / c,
        }

    return summary


# ================================================================
# Report formatting
# ================================================================

def format_report(summary: EvalSummary, results: List[EvalItemResult]) -> str:
    """Readable text report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  RAG EVALUATION REPORT")
    lines.append("=" * 70)
    lines.append("")

    lines.append(f"  Total items:        {summary.total}")
    lines.append(f"    In-scope:         {summary.in_scope_total}")
    lines.append(f"    Out-of-scope:     {summary.out_of_scope_total}")
    lines.append("")

    lines.append("  --- Retrieval Metrics ---")
    lines.append(f"  Hit Rate:           {summary.hit_rate*100:.1f}%   "
                 f"({summary.hit_rate:.3f})")
    lines.append(f"  MRR:                {summary.mrr:.3f}")
    lines.append("")

    lines.append("  --- Answer Metrics ---")
    lines.append(f"  Answer Correctness: {summary.answer_correct_rate*100:.1f}%   "
                 f"({summary.answer_correct_rate:.3f})")
    lines.append(f"  Source Correctness: {summary.source_correct_rate*100:.1f}%   "
                 f"({summary.source_correct_rate:.3f})")
    lines.append("")

    if summary.faithfulness_avg is not None:
        lines.append("  --- Faithfulness (LLM judge) ---")
        lines.append(f"  Avg Score:          {summary.faithfulness_avg:.3f}   "
                     f"(n={summary.faithfulness_count})")
        lines.append("")

    lines.append("  --- Not-Found Handling ---")
    lines.append(f"  Accuracy:           {summary.not_found_accuracy*100:.1f}%")
    lines.append("")

    lines.append(f"  Avg Time / Query:   {summary.avg_elapsed:.2f}s")
    lines.append("")

    if summary.per_category:
        lines.append("  --- Per Category ---")
        for cat, stats in sorted(summary.per_category.items()):
            lines.append(
                f"  {cat:15s} n={stats['count']:3d}  "
                f"correct={stats['answer_correct_rate']*100:5.1f}%  "
                f"hit={stats['hit_rate']*100:5.1f}%"
            )
        lines.append("")

    failures = [r for r in results if not r.answer_correct and not r.should_be_not_found]
    if failures:
        lines.append("  --- Failures ---")
        for r in failures:
            lines.append(f"  [{r.item_id}] {r.question}")
            lines.append(f"      Missing keywords: {r.missing_keywords}")
            lines.append(f"      Answer: {r.answer[:100]}...")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def summary_to_dict(summary: EvalSummary) -> Dict[str, Any]:
    """JSON-serializable summary."""
    return {
        "total": summary.total,
        "in_scope_total": summary.in_scope_total,
        "out_of_scope_total": summary.out_of_scope_total,
        "hit_rate": round(summary.hit_rate, 4),
        "mrr": round(summary.mrr, 4),
        "answer_correct_rate": round(summary.answer_correct_rate, 4),
        "source_correct_rate": round(summary.source_correct_rate, 4),
        "faithfulness_avg": (
            round(summary.faithfulness_avg, 4)
            if summary.faithfulness_avg is not None
            else None
        ),
        "not_found_accuracy": round(summary.not_found_accuracy, 4),
        "avg_elapsed": round(summary.avg_elapsed, 2),
        "per_category": summary.per_category,
    }


def item_to_dict(r: EvalItemResult) -> Dict[str, Any]:
    return {
        "item_id": r.item_id,
        "category": r.category,
        "question": r.question,
        "hit": r.hit,
        "reciprocal_rank": round(r.reciprocal_rank, 4),
        "retrieved_pages": r.retrieved_pages,
        "answer": r.answer[:400],
        "answer_correct": r.answer_correct,
        "missing_keywords": r.missing_keywords,
        "source_correct": r.source_correct,
        "source_pages": r.source_pages,
        "found_in_documents": r.found_in_documents,
        "should_be_not_found": r.should_be_not_found,
        "not_found_correct": r.not_found_correct,
        "faithfulness_score": r.faithfulness_score,
        "elapsed": round(r.elapsed, 2),
    }