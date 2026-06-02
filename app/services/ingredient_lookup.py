"""Fuzzy-match extracted ingredient strings to Postgres ingredient rows.

Strategy per extracted ingredient (in order, first hit wins):
  1. Try to extract an E-number (e.g., "E322" from "Soya lecithin E322")
     and exact-match against the `e_number` column. Highest signal.
  2. Normalize the string and try exact-match against canonical_name or aliases.
  3. Fuzzy-match against the union of all canonical_names + aliases.
     Accept matches above MIN_FUZZY_SCORE.
  4. Otherwise: mark as unknown.

Tunables are constants at the top.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingredient import Ingredient

MIN_FUZZY_SCORE = 82
E_NUMBER_RE = re.compile(r"\bE\s?(\d{3,4}[a-z]?)\b", re.IGNORECASE)

PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)\s*")
PERCENTAGE_RE = re.compile(r"\s*\d{1,3}\s*%\s*")


@dataclass
class IngredientMatch:
    raw: str
    matched: Ingredient | None
    score: float
    method: str  # "e_number", "exact", "fuzzy", "unmatched"


def _normalize(raw: str) -> str:
    """Lowercase, strip parentheticals, percentages, punctuation; collapse whitespace."""
    s = raw.lower()
    s = PARENTHETICAL_RE.sub(" ", s)
    s = PERCENTAGE_RE.sub(" ", s)
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_e_number(raw: str) -> str | None:
    """Pull an E-number out of strings like 'Soya lecithin (E322)' or 'E150c'."""
    match = E_NUMBER_RE.search(raw)
    if not match:
        return None
    return f"E{match.group(1).lower()}"


async def lookup_ingredients(
    session: AsyncSession, extracted: list[str]
) -> list[IngredientMatch]:
    """Match each extracted ingredient string to a Postgres row or return None."""
    all_ingredients = (await session.scalars(select(Ingredient))).all()

    alias_to_ingredient: dict[str, Ingredient] = {}
    for ing in all_ingredients:
        alias_to_ingredient[_normalize(ing.canonical_name)] = ing
        for alias in ing.aliases:
            alias_to_ingredient[_normalize(alias)] = ing

    e_number_to_ingredient: dict[str, Ingredient] = {
        ing.e_number.upper(): ing for ing in all_ingredients if ing.e_number
    }

    candidate_strings = list(alias_to_ingredient.keys())

    results: list[IngredientMatch] = []
    for raw in extracted:
        e_num = _extract_e_number(raw)
        if e_num and e_num.upper() in e_number_to_ingredient:
            results.append(
                IngredientMatch(
                    raw=raw,
                    matched=e_number_to_ingredient[e_num.upper()],
                    score=100.0,
                    method="e_number",
                )
            )
            continue

        normalized = _normalize(raw)
        if not normalized:
            results.append(
                IngredientMatch(raw=raw, matched=None, score=0.0, method="unmatched")
            )
            continue

        if normalized in alias_to_ingredient:
            results.append(
                IngredientMatch(
                    raw=raw,
                    matched=alias_to_ingredient[normalized],
                    score=100.0,
                    method="exact",
                )
            )
            continue

        best_wratio = process.extractOne(
            normalized,
            candidate_strings,
            scorer=fuzz.WRatio,
            score_cutoff=MIN_FUZZY_SCORE,
        )
        best_token = process.extractOne(
            normalized,
            candidate_strings,
            scorer=fuzz.token_set_ratio,
            score_cutoff=MIN_FUZZY_SCORE,
        )

        candidates_to_consider = [c for c in (best_wratio, best_token) if c is not None]
        if candidates_to_consider:
            candidate, score, _ = max(candidates_to_consider, key=lambda c: c[1])
            results.append(
                IngredientMatch(
                    raw=raw,
                    matched=alias_to_ingredient[candidate],
                    score=float(score),
                    method="fuzzy",
                )
            )
            continue

        results.append(
            IngredientMatch(raw=raw, matched=None, score=0.0, method="unmatched")
        )

    return results
