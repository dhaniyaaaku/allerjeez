"""Populate the `ingredients` table from curated public-domain CSVs in /data.

Sources (all bundled in the repo):
  - data/allergens.csv         FDA top-9 + EU top-14 allergens with synonyms
  - data/additives.csv         Common E-numbered additives with regulatory flags
  - data/iarc_carcinogens.csv  Hand-curated IARC carcinogens relevant to food

Run with: uv run python -m scripts.ingest_ingredients

Idempotent: safe to re-run. Upserts on canonical_name.
"""

from __future__ import annotations

import asyncio
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import engine
from app.models import Base
from app.models.ingredient import Ingredient

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALLERGENS_CSV = DATA_DIR / "allergens.csv"
ADDITIVES_CSV = DATA_DIR / "additives.csv"
IARC_CSV = DATA_DIR / "iarc_carcinogens.csv"


@dataclass
class StagedIngredient:
    """Intermediate representation built up before insertion."""

    canonical_name: str
    aliases: set[str] = field(default_factory=set)
    e_number: str | None = None
    category: str | None = None
    is_allergen: bool = False
    allergen_group: str | None = None
    iarc_group: str | None = None
    regulatory_flags: dict = field(default_factory=dict)
    common_concerns: set[str] = field(default_factory=set)
    notes: str | None = None
    sources: set[str] = field(default_factory=set)


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-]+", "", text)
    return text.strip("-")


def _split_semicolon(s: str | None) -> set[str]:
    if not s:
        return set()
    return {part.strip() for part in s.split(";") if part.strip()}


def stage_allergens(csv_path: Path) -> dict[str, StagedIngredient]:
    staged: dict[str, StagedIngredient] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row["canonical_name"].strip()
            if not canonical:
                continue
            slug = slugify(canonical)
            staged[slug] = StagedIngredient(
                canonical_name=canonical,
                aliases=_split_semicolon(row.get("aliases")),
                category="allergen",
                is_allergen=True,
                allergen_group=row.get("allergen_group") or canonical,
                common_concerns=_split_semicolon(row.get("common_concerns")),
                notes=row.get("notes") or None,
                sources=_split_semicolon(row.get("source_url")),
            )
    return staged


def stage_additives(csv_path: Path) -> dict[str, StagedIngredient]:
    staged: dict[str, StagedIngredient] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row["canonical_name"].strip()
            if not canonical:
                continue
            slug = slugify(canonical)
            e_number = (row.get("e_number") or "").strip() or None
            staged[slug] = StagedIngredient(
                canonical_name=canonical,
                aliases=_split_semicolon(row.get("aliases")),
                e_number=e_number,
                category=row.get("additive_subcategory") or "additive",
                common_concerns=_split_semicolon(row.get("common_concerns")),
                notes=row.get("notes") or None,
                sources=_split_semicolon(row.get("source_url")),
            )
    return staged


def stage_iarc(csv_path: Path) -> dict[str, StagedIngredient]:
    staged: dict[str, StagedIngredient] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row["canonical_name"].strip()
            if not canonical:
                continue
            slug = slugify(canonical)
            staged[slug] = StagedIngredient(
                canonical_name=canonical,
                aliases=_split_semicolon(row.get("aliases")),
                category=row.get("category") or None,
                iarc_group=row.get("iarc_group") or None,
                common_concerns=_split_semicolon(row.get("common_concerns")),
                notes=row.get("notes") or None,
                sources=_split_semicolon(row.get("source_url")),
            )
    return staged


def merge_staged(
    *sources: dict[str, StagedIngredient],
) -> dict[str, StagedIngredient]:
    """Merge entries sharing a slug, unioning collection fields."""
    merged: dict[str, StagedIngredient] = {}
    for source in sources:
        for slug, entry in source.items():
            if slug not in merged:
                merged[slug] = entry
                continue
            existing = merged[slug]
            existing.aliases |= entry.aliases
            existing.common_concerns |= entry.common_concerns
            existing.sources |= entry.sources
            existing.e_number = existing.e_number or entry.e_number
            existing.category = existing.category or entry.category
            existing.is_allergen = existing.is_allergen or entry.is_allergen
            existing.allergen_group = existing.allergen_group or entry.allergen_group
            existing.iarc_group = existing.iarc_group or entry.iarc_group
            existing.notes = existing.notes or entry.notes
            existing.regulatory_flags = {
                **entry.regulatory_flags,
                **existing.regulatory_flags,
            }
    return merged


def staged_to_rows(staged: dict[str, StagedIngredient]) -> list[dict]:
    rows: list[dict] = []
    for entry in staged.values():
        rows.append(
            {
                "canonical_name": entry.canonical_name,
                "aliases": sorted(entry.aliases),
                "e_number": entry.e_number,
                "category": entry.category,
                "is_allergen": entry.is_allergen,
                "allergen_group": entry.allergen_group,
                "iarc_group": entry.iarc_group,
                "regulatory_flags": entry.regulatory_flags,
                "common_concerns": sorted(entry.common_concerns),
                "notes": entry.notes,
                "sources": sorted(entry.sources),
            }
        )
    return rows


async def upsert_rows(rows: list[dict]) -> int:
    if not rows:
        return 0

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        stmt = insert(Ingredient).values(rows)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in Ingredient.__table__.columns
            if col.name not in {"id", "canonical_name", "created_at"}
        }
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["canonical_name"],
            set_=update_cols,
        )
        await conn.execute(upsert_stmt)

    return len(rows)


async def main() -> None:
    print("Allerjeez :: ingredient ingestion (offline / bundled data)")
    print("=" * 60)

    print(f"\n[1/4] Loading allergens from {ALLERGENS_CSV.name}")
    allergens = stage_allergens(ALLERGENS_CSV)
    print(f"  Loaded {len(allergens)} allergen entries")

    print(f"\n[2/4] Loading additives from {ADDITIVES_CSV.name}")
    additives = stage_additives(ADDITIVES_CSV)
    print(f"  Loaded {len(additives)} additive entries")

    print(f"\n[3/4] Loading IARC carcinogens from {IARC_CSV.name}")
    iarc = stage_iarc(IARC_CSV)
    print(f"  Loaded {len(iarc)} IARC entries")

    merged = merge_staged(allergens, additives, iarc)
    print(f"\n  Merged total: {len(merged)} unique ingredients")

    category_counts: dict[str | None, int] = defaultdict(int)
    iarc_counts: dict[str | None, int] = defaultdict(int)
    allergen_count = 0
    for entry in merged.values():
        category_counts[entry.category] += 1
        if entry.iarc_group:
            iarc_counts[entry.iarc_group] += 1
        if entry.is_allergen:
            allergen_count += 1

    print(f"  Allergen rows: {allergen_count}")
    print("  By category:")
    for cat, count in sorted(category_counts.items(), key=lambda kv: -kv[1]):
        print(f"    {cat or '(none)'}: {count}")
    if iarc_counts:
        print("  By IARC group:")
        for group, count in sorted(iarc_counts.items()):
            print(f"    Group {group}: {count}")

    print("\n[4/4] Upserting into Postgres")
    rows = staged_to_rows(merged)
    inserted = await upsert_rows(rows)
    print(f"  Upserted {inserted} rows.")

    async with engine.begin() as conn:
        sample = await conn.scalar(select(Ingredient.id).limit(1))
        print(f"  Sample lookup OK (first id seen: {sample}).")

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
