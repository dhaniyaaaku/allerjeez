"""Run the gold set through the FULL extraction + safety report pipeline and report metrics.

Usage:
    uv run python -m eval.run_eval                   # full run
    uv run python -m eval.run_eval --limit 5         # quick smoke test
    uv run python -m eval.run_eval --force           # ignore the cache, redo all
    uv run python -m eval.run_eval --output eval/results.md

Reads `eval/gold_labels.jsonl`, calls the live extraction pipeline + the rule-based
matcher + the safety report builder for each entry, then compares the report's
flagged allergens/carcinogens against ground truth.

This measures the system as users actually see it (including the alias-aware
allergen matcher and LLM fallback for unknowns), not a naive text match.

Resumable: per-entry raw results are cached in `eval/.cache_results.jsonl`.

Metrics:
- Ingredient recall:    pct of expected ingredients found in Gemini's extraction
- Ingredient precision: pct of extracted that were really expected
- Ingredient F1:        harmonic mean of the two
- Allergen recall:      pct of expected allergens caught by the safety report
                        (checks personal_allergens + other_allergens by allergen_group)
- Carcinogen recall:    pct of expected carcinogens caught by the safety report
- Latency:              p50, p95, p99 per scan (end-to-end pipeline)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.models.user import User
from app.services.ingredient_lookup import lookup_ingredients
from app.services.llm_ingredient_lookup import classify_unknowns
from app.services.safety_report import build_safety_report
from app.services.vision import extract_ingredients_from_image

EVAL_DIR = Path(__file__).resolve().parent
LABELS_PATH = EVAL_DIR / "gold_labels.jsonl"
CACHE_PATH = EVAL_DIR / ".cache_results.jsonl"
DEFAULT_RESULTS = EVAL_DIR / "results.md"

ING_FUZZY_THRESHOLD = 80
SECONDS_BETWEEN_CALLS = 5.0


def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\d+\s*%", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _fuzzy_match(needle: str, haystack: list[str]) -> bool:
    needle_n = _normalize(needle)
    if not needle_n:
        return False
    for item in haystack:
        if fuzz.token_set_ratio(needle_n, _normalize(item)) >= ING_FUZZY_THRESHOLD:
            return True
    return False


def _mime_for(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    cache: dict[str, dict] = {}
    for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "image" in entry and not entry.get("skipped"):
            cache[entry["image"]] = entry
    return cache


def _append_cache(result: dict) -> None:
    if result.get("skipped"):
        return
    with CACHE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")


@dataclass
class EvalUser:
    """Stand-in for a real User row. The safety report builder reads only
    `allergies` off the user, so a dataclass with the right field is enough."""

    allergies: list[str]
    dietary_preferences: list[str]
    conditions: list[str]


async def _evaluate_one(entry: dict, session: AsyncSession) -> dict:
    image_path = EVAL_DIR / entry["image"]
    if not image_path.exists():
        return {
            "image": entry["image"],
            "error": f"file not found: {image_path}",
            "skipped": True,
        }

    image_bytes = image_path.read_bytes()
    mime = _mime_for(image_path)

    t0 = time.perf_counter()
    try:
        # 1. Extraction
        extraction = await extract_ingredients_from_image(image_bytes, mime)
        # 2. Rule-based matching
        matches = await lookup_ingredients(session, extraction.ingredients)
        # 3. LLM fallback for unknowns (same path users hit)
        matches = await classify_unknowns(session, matches)
        # 4. Build safety report against a "user with all expected allergens"
        #    so personal_allergens gets populated for every expected allergen.
        eval_user = EvalUser(
            allergies=list(entry.get("expected_allergens", [])),
            dietary_preferences=[],
            conditions=[],
        )
        report = build_safety_report(
            extraction=extraction,
            matches=matches,
            user=eval_user,  # type: ignore[arg-type]
        )
    except Exception as exc:
        return {
            "image": entry["image"],
            "error": str(exc),
            "skipped": True,
        }
    elapsed = time.perf_counter() - t0

    # ---- Ingredient extraction metrics (Gemini-level) ----
    expected_ings = entry.get("expected_ingredients", [])
    extracted_ings = extraction.ingredients

    tp_recall = sum(1 for e in expected_ings if _fuzzy_match(e, extracted_ings))
    tp_precision = sum(1 for x in extracted_ings if _fuzzy_match(x, expected_ings))

    recall = tp_recall / len(expected_ings) if expected_ings else 0.0
    precision = tp_precision / len(extracted_ings) if extracted_ings else 0.0
    f1 = (
        2 * recall * precision / (recall + precision)
        if (recall + precision) > 0
        else 0.0
    )

    # ---- Allergen metrics (system-level, via safety report) ----
    expected_allergens = [a.lower() for a in entry.get("expected_allergens", [])]
    flagged_allergen_groups = {
        (f.ingredient_name or "").lower()
        for f in report.personal_allergens + report.other_allergens
    }
    # The safety report sets ingredient_name to the canonical_name (e.g. "milk", "soy")
    # which matches our allergen group strings directly.

    # But personal_allergen entries set ingredient_name = canonical_name, while the
    # underlying allergen group lives elsewhere. So we extend by checking allergen
    # categories named in the personal_allergens "reason" too.
    # Simpler: use the canonical_name set directly. For aliases like "lecithin (soy)"
    # the matcher resolves to canonical "soy-lecithin" which IS the allergen.
    found_allergens: list[str] = []
    missed_allergens: list[str] = []
    for allergen in expected_allergens:
        # Direct match on canonical name, OR substring match (e.g. "soy" inside "soy-lecithin")
        if any(allergen == g or allergen in g for g in flagged_allergen_groups):
            found_allergens.append(allergen)
        else:
            missed_allergens.append(allergen)

    allergen_recall = (
        len(found_allergens) / len(expected_allergens) if expected_allergens else 1.0
    )

    # ---- Carcinogen metrics ----
    expected_carcs = [c.lower() for c in entry.get("expected_carcinogens", [])]
    flagged_carc_names = {(f.ingredient_name or "").lower() for f in report.carcinogens}
    found_carcs: list[str] = []
    missed_carcs: list[str] = []
    for carc in expected_carcs:
        if any(carc == n or carc in n or n in carc for n in flagged_carc_names):
            found_carcs.append(carc)
        else:
            missed_carcs.append(carc)
    carcinogen_recall = (
        len(found_carcs) / len(expected_carcs) if expected_carcs else 1.0
    )

    return {
        "image": entry["image"],
        "product_name": entry.get("product_name"),
        "n_expected": len(expected_ings),
        "n_extracted": len(extracted_ings),
        "tp_recall": tp_recall,
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "allergen_recall": allergen_recall,
        "expected_allergens": expected_allergens,
        "missed_allergens": missed_allergens,
        "carcinogen_recall": carcinogen_recall,
        "expected_carcinogens": expected_carcs,
        "missed_carcinogens": missed_carcs,
        "flagged_allergens": sorted(flagged_allergen_groups),
        "flagged_carcinogens": sorted(flagged_carc_names),
        "latency_s": elapsed,
        "verdict": report.overall_verdict,
        "skipped": False,
    }


def _summarize(results: list[dict]) -> dict:
    real = [r for r in results if not r.get("skipped")]
    if not real:
        return {"empty": True}

    recalls = [r["recall"] for r in real]
    precisions = [r["precision"] for r in real]
    f1s = [r["f1"] for r in real]
    allergen_recalls = [r["allergen_recall"] for r in real]
    carcinogen_recalls = [r.get("carcinogen_recall", 1.0) for r in real]
    latencies = [r["latency_s"] for r in real]

    def pct(xs: list[float]) -> float:
        return 100 * statistics.mean(xs)

    def p(xs: list[float], q: float) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        k = int(round(q * (len(s) - 1)))
        return s[k]

    return {
        "n": len(real),
        "ingredient_recall_pct": pct(recalls),
        "ingredient_precision_pct": pct(precisions),
        "ingredient_f1_pct": pct(f1s),
        "allergen_recall_pct": pct(allergen_recalls),
        "carcinogen_recall_pct": pct(carcinogen_recalls),
        "latency_p50_s": p(latencies, 0.5),
        "latency_p95_s": p(latencies, 0.95),
        "latency_p99_s": p(latencies, 0.99),
    }


def _format_results(summary: dict, results: list[dict], total: int) -> str:
    if summary.get("empty"):
        return "No valid eval entries — gold set is empty or all entries errored.\n"

    lines: list[str] = []
    lines.append("# Allerjeez extraction + safety pipeline eval - results\n")
    lines.append(
        f"_Run at_: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`\n"
    )
    lines.append(f"_Gold set size_: **{total}** images ({summary['n']} scored)\n")
    lines.append(
        "_Methodology: each image runs end-to-end through Gemini Vision -> "
        "rule-based matcher -> LLM fallback -> safety report builder. "
        "Allergen and carcinogen metrics check whether the SAFETY REPORT "
        "flagged the expected categories, not naive substring matching._\n"
    )
    lines.append("\n## Aggregate metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Ingredient recall | **{summary['ingredient_recall_pct']:.1f}%** |")
    lines.append(f"| Ingredient precision | {summary['ingredient_precision_pct']:.1f}% |")
    lines.append(f"| Ingredient F1 | {summary['ingredient_f1_pct']:.1f}% |")
    lines.append(f"| **Allergen recall** | **{summary['allergen_recall_pct']:.1f}%** |")
    lines.append(f"| Carcinogen recall | {summary['carcinogen_recall_pct']:.1f}% |")
    lines.append(f"| Latency p50 (end-to-end) | {summary['latency_p50_s']:.2f}s |")
    lines.append(f"| Latency p95 (end-to-end) | {summary['latency_p95_s']:.2f}s |")
    lines.append(f"| Latency p99 (end-to-end) | {summary['latency_p99_s']:.2f}s |\n")

    lines.append("## Per-image results\n")
    lines.append(
        "| Image | Recall | Precision | F1 | Allergen recall | "
        "Missed allergens | Carc recall | Missed carcinogens | Verdict |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        if r.get("skipped"):
            lines.append(
                f"| {r['image']} | _skipped_ | | | | | | | {r.get('error', '')} |"
            )
            continue
        missed_a = ", ".join(r["missed_allergens"]) or "—"
        missed_c = ", ".join(r["missed_carcinogens"]) or "—"
        lines.append(
            f"| {r['image']} | {r['recall'] * 100:.0f}% | "
            f"{r['precision'] * 100:.0f}% | {r['f1'] * 100:.0f}% | "
            f"{r['allergen_recall'] * 100:.0f}% | {missed_a} | "
            f"{r['carcinogen_recall'] * 100:.0f}% | {missed_c} | "
            f"{r.get('verdict', '')} |"
        )
    return "\n".join(lines) + "\n"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None, help="Eval only the first N entries"
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_RESULTS, help="Where to write results"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the per-entry cache and redo every image.",
    )
    args = parser.parse_args()

    if args.force and CACHE_PATH.exists():
        CACHE_PATH.unlink()

    if not LABELS_PATH.exists():
        print(f"Missing {LABELS_PATH}. Add some gold labels first.")
        return

    entries: list[dict] = []
    with LABELS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entries.append(json.loads(line))

    if args.limit is not None:
        entries = entries[: args.limit]

    if not entries:
        print("Gold labels file is empty.")
        return

    cached = _load_cache()
    # Old cache may not have the new fields. Treat entries missing the new
    # carcinogen_recall key as stale so we redo them.
    cached = {
        k: v for k, v in cached.items()
        if "carcinogen_recall" in v and "flagged_allergens" in v
    }
    print(f"Running eval on {len(entries)} gold entries...")
    if cached:
        print(f"Found {len(cached)} usable cached results; will skip those.")
    print(f"Pacing: ~{SECONDS_BETWEEN_CALLS}s between Gemini calls\n")

    results: list[dict] = []
    pending: list[dict] = []
    for entry in entries:
        if entry["image"] in cached:
            results.append(cached[entry["image"]])
        else:
            pending.append(entry)

    async with SessionLocal() as session:
        for i, entry in enumerate(pending, 1):
            print(
                f"  [{i}/{len(pending)}] {entry['image']}", end=" ... ", flush=True
            )
            result = await _evaluate_one(entry, session)
            if result.get("skipped"):
                print(f"SKIPPED ({str(result.get('error', ''))[:120]})")
            else:
                print(
                    f"recall={result['recall'] * 100:.0f}% "
                    f"allergens={result['allergen_recall'] * 100:.0f}% "
                    f"carc={result['carcinogen_recall'] * 100:.0f}% "
                    f"({result['latency_s']:.2f}s)"
                )
                _append_cache(result)
            results.append(result)

            if i < len(pending):
                await asyncio.sleep(SECONDS_BETWEEN_CALLS)

    await engine.dispose()

    summary = _summarize(results)
    report = _format_results(summary, results, total=len(entries))

    args.output.write_text(report, encoding="utf-8")
    print()
    print(report)
    print(f"\nResults written to {args.output}")
    if any(r.get("skipped") for r in results):
        print(
            "\nSome entries were skipped (likely rate limit). "
            "Rerun the same command later to fill them in — cache will keep the rest."
        )


if __name__ == "__main__":
    asyncio.run(main())
