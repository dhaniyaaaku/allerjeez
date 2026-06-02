"""Run the gold set through the extraction pipeline and report metrics.

Usage:
    uv run python -m eval.run_eval                   # full run
    uv run python -m eval.run_eval --limit 5         # quick smoke test
    uv run python -m eval.run_eval --force           # ignore the cache, redo all
    uv run python -m eval.run_eval --output eval/results.md

Reads `eval/gold_labels.jsonl`, calls the live extraction pipeline for each entry,
compares extracted ingredients/allergens to ground truth, prints a metrics table,
and writes results to `eval/results.md`.

Resumable: per-entry raw results are cached in `eval/.cache_results.jsonl`.
If you hit a rate limit mid-run, rerun without --force to resume.

Metrics:
- Ingredient recall:    pct of expected ingredients found
- Ingredient precision: pct of extracted that were really expected
- Ingredient F1:        harmonic mean of the two
- Allergen recall:      pct of expected allergens caught by the system
- Latency:              p50, p95, p99 per scan
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

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
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")


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


async def _evaluate_one(entry: dict) -> dict:
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
        extraction = await extract_ingredients_from_image(image_bytes, mime)
    except Exception as exc:
        return {
            "image": entry["image"],
            "error": str(exc),
            "skipped": True,
        }
    elapsed = time.perf_counter() - t0

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

    expected_allergens = [a.lower() for a in entry.get("expected_allergens", [])]
    found_allergens: list[str] = []
    for allergen in expected_allergens:
        if _fuzzy_match(allergen, extracted_ings):
            found_allergens.append(allergen)

    allergen_recall = (
        len(found_allergens) / len(expected_allergens) if expected_allergens else 1.0
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
        "missed_allergens": [a for a in expected_allergens if a not in found_allergens],
        "latency_s": elapsed,
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
        "latency_p50_s": p(latencies, 0.5),
        "latency_p95_s": p(latencies, 0.95),
        "latency_p99_s": p(latencies, 0.99),
    }


def _format_results(summary: dict, results: list[dict], total: int) -> str:
    if summary.get("empty"):
        return "No valid eval entries — gold set is empty or all entries errored.\n"

    lines: list[str] = []
    lines.append("# Allerjeez extraction eval - results\n")
    lines.append(
        f"_Run at_: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`\n"
    )
    lines.append(f"_Gold set size_: **{total}** images ({summary['n']} scored)\n")
    lines.append("\n## Aggregate metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Ingredient recall | **{summary['ingredient_recall_pct']:.1f}%** |")
    lines.append(f"| Ingredient precision | {summary['ingredient_precision_pct']:.1f}% |")
    lines.append(f"| Ingredient F1 | {summary['ingredient_f1_pct']:.1f}% |")
    lines.append(f"| **Allergen recall** | **{summary['allergen_recall_pct']:.1f}%** |")
    lines.append(f"| Latency p50 | {summary['latency_p50_s']:.2f}s |")
    lines.append(f"| Latency p95 | {summary['latency_p95_s']:.2f}s |")
    lines.append(f"| Latency p99 | {summary['latency_p99_s']:.2f}s |\n")

    lines.append("## Per-image results\n")
    lines.append(
        "| Image | Recall | Precision | F1 | Allergen recall | Missed allergens |"
    )
    lines.append("|---|---|---|---|---|---|")
    for r in results:
        if r.get("skipped"):
            lines.append(
                f"| {r['image']} | _skipped_ | | | | {r.get('error', '')} |"
            )
            continue
        missed = ", ".join(r["missed_allergens"]) or "—"
        lines.append(
            f"| {r['image']} | {r['recall'] * 100:.0f}% | "
            f"{r['precision'] * 100:.0f}% | {r['f1'] * 100:.0f}% | "
            f"{r['allergen_recall'] * 100:.0f}% | {missed} |"
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
    print(f"Running eval on {len(entries)} gold entries...")
    if cached:
        print(f"Found {len(cached)} cached results; will skip those.")
    print(f"Pacing: ~{SECONDS_BETWEEN_CALLS}s between Gemini calls\n")

    results: list[dict] = []
    pending: list[dict] = []
    for entry in entries:
        if entry["image"] in cached:
            results.append(cached[entry["image"]])
        else:
            pending.append(entry)

    for i, entry in enumerate(pending, 1):
        print(f"  [{i}/{len(pending)}] {entry['image']}", end=" ... ", flush=True)
        result = await _evaluate_one(entry)
        if result.get("skipped"):
            print(f"SKIPPED ({result.get('error', '')})")
        else:
            print(
                f"recall={result['recall'] * 100:.0f}% "
                f"allergens={result['allergen_recall'] * 100:.0f}% "
                f"({result['latency_s']:.2f}s)"
            )
            _append_cache(result)
        results.append(result)

        if i < len(pending):
            await asyncio.sleep(SECONDS_BETWEEN_CALLS)

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
