"""Bootstrap gold labels by running every image through the extraction pipeline.

Produces a `gold_labels.jsonl` you then HAND-EDIT to fix Gemini's mistakes
and add allergen ground truth.

Usage:
    uv run python -m eval.bootstrap_labels

By default, resumes from where the last run left off — already-classified images
are kept and only missing/errored ones are reclassified. Pass --force to start over.

Free-tier-friendly: paces calls to stay under Gemini's 15 req/min cap.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.services.vision import extract_ingredients_from_image

EVAL_DIR = Path(__file__).resolve().parent
IMAGES_DIR = EVAL_DIR / "gold_images"
OUTPUT_PATH = EVAL_DIR / "gold_labels.jsonl"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Free tier of Gemini Flash is 15 req/min. We pace at 5s between calls
# (= 12 req/min) to leave headroom.
SECONDS_BETWEEN_CALLS = 5.0


def _mime_for(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")


def _load_existing() -> dict[str, dict]:
    """Read existing gold_labels.jsonl into {image_rel_path: entry}."""
    existing: dict[str, dict] = {}
    if not OUTPUT_PATH.exists():
        return existing
    for line in OUTPUT_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "image" in entry:
            existing[entry["image"]] = entry
    return existing


def _is_resolved(entry: dict) -> bool:
    """An entry is 'resolved' if it has at least one extracted ingredient."""
    if not entry:
        return False
    if entry.get("expected_ingredients"):
        return True
    return False


async def _classify_one(image_path: Path):
    image_bytes = image_path.read_bytes()
    return await extract_ingredients_from_image(image_bytes, _mime_for(image_path))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-classify every image even if already in gold_labels.jsonl",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Bootstrap only the first N images",
    )
    args = parser.parse_args()

    images = sorted(p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if args.limit:
        images = images[: args.limit]

    if not images:
        print(f"No images in {IMAGES_DIR}. Add some first.")
        return

    existing = {} if args.force else _load_existing()
    print(f"Bootstrapping {len(images)} images...")
    if existing:
        print(f"Found {len(existing)} existing entries; will keep resolved ones.")
    print(f"Pacing: ~{SECONDS_BETWEEN_CALLS}s between Gemini calls\n")

    entries_by_image: dict[str, dict] = dict(existing)
    pending = []
    for image_path in images:
        rel = f"gold_images/{image_path.name}"
        if not args.force and _is_resolved(entries_by_image.get(rel, {})):
            print(f"  KEEP   {rel}  (already labeled with {len(entries_by_image[rel].get('expected_ingredients', []))} ingredients)")
            continue
        pending.append((rel, image_path))

    if not pending:
        print("\nAll images already have labels. Nothing to do.")
        return

    print(f"\n{len(pending)} images need classification.\n")

    for i, (rel, image_path) in enumerate(pending, 1):
        print(f"  [{i}/{len(pending)}] {rel}", end=" ... ", flush=True)
        try:
            extraction = await _classify_one(image_path)
            entries_by_image[rel] = {
                "image": rel,
                "product_name": extraction.product_name,
                "expected_ingredients": extraction.ingredients,
                "expected_allergens": [],
                "expected_carcinogens": [],
                "notes": "DRAFT - needs human review",
            }
            print(
                f"ok ({len(extraction.ingredients)} ingredients, "
                f"confidence={extraction.confidence:.0%})"
            )
        except Exception as exc:
            print(f"ERROR ({exc})")
            entries_by_image[rel] = {
                "image": rel,
                "product_name": None,
                "expected_ingredients": [],
                "expected_allergens": [],
                "expected_carcinogens": [],
                "notes": f"DRAFT - extraction errored: {exc}",
            }

        # Persist incrementally so we don't lose progress on a hard crash
        _write(entries_by_image, images)

        if i < len(pending):
            await asyncio.sleep(SECONDS_BETWEEN_CALLS)

    _write(entries_by_image, images)

    resolved = sum(1 for e in entries_by_image.values() if _is_resolved(e))
    failed = len(entries_by_image) - resolved
    print(f"\nDone. {resolved} resolved, {failed} failed/empty.")
    print(f"Output: {OUTPUT_PATH}")
    if failed:
        print(
            "\nRerun this script (without --force) to retry only the failed images."
        )


def _write(entries_by_image: dict[str, dict], images: list[Path]) -> None:
    """Write entries in the same order as `images` so the file is deterministic."""
    lines: list[str] = []
    seen = set()
    for image_path in images:
        rel = f"gold_images/{image_path.name}"
        if rel in entries_by_image:
            lines.append(json.dumps(entries_by_image[rel], ensure_ascii=False))
            seen.add(rel)
    # any entries that don't match a file we found (rare) get tacked on
    for rel, entry in entries_by_image.items():
        if rel not in seen:
            lines.append(json.dumps(entry, ensure_ascii=False))
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
