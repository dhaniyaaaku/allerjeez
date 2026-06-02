"""LLM-based ingredient classifier — fallback for ingredients not in the KB.

Strategy:
  1. For each "unknown" ingredient (rule-based lookup returned no match),
     normalize and check Postgres again (might have been LLM-classified before).
  2. If still missing, ask Gemini to classify. Validates via Pydantic.
  3. Save classification to Postgres with source tag "llm:<model>".
  4. Return as a regular IngredientMatch.

The LLM never overrides authoritative entries: it only fills empty slots.
"""

from __future__ import annotations

import logging
import re

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ingredient import Ingredient
from app.schemas.llm_lookup import LLMIngredientClassification
from app.services.ingredient_lookup import IngredientMatch, _normalize

logger = logging.getLogger(__name__)

LLM_SOURCE_PREFIX = "llm:"

CLASSIFY_PROMPT = """You classify single food-ingredient strings into a structured object.

You will be given ONE ingredient string as it appeared on a real food product label.
Your output must follow the JSON schema strictly.

Rules:
- canonical_name: lowercase, hyphenated, no punctuation, no percentages, no parentheticals.
- is_real_food_ingredient: false for label noise like '38%', 'see back', 'manufactured by ...'.
- category: pick the best of the enumerated values; never invent new ones.
- has_known_concerns: true ONLY for ingredients with documented safety / regulatory / health concerns
  (e.g. trans fats, banned-in-EU additives, IARC-flagged). Everyday foods (sugar, salt, cocoa butter)
  are NOT a concern even though over-consumption is unhealthy.
- concerns: short hyphenated tags. Empty if no concerns.
- e_number: include only if this is a well-known E-numbered additive."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


WORD_RE = re.compile(r"[a-z0-9]+")


def _slug(text: str) -> str:
    parts = WORD_RE.findall(text.lower())
    return "-".join(parts).strip("-")


async def _lookup_cached(
    session: AsyncSession, raw: str
) -> Ingredient | None:
    normalized = _normalize(raw)
    if not normalized:
        return None
    candidate_slug = _slug(normalized)
    if not candidate_slug:
        return None
    return await session.scalar(
        select(Ingredient).where(Ingredient.canonical_name == candidate_slug)
    )


async def _classify_with_gemini(raw: str) -> LLMIngredientClassification | None:
    client = _get_client()
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_vision_model,
            contents=[f"Classify this food ingredient string: {raw!r}"],
            config=types.GenerateContentConfig(
                system_instruction=CLASSIFY_PROMPT,
                response_mime_type="application/json",
                response_schema=LLMIngredientClassification,
                temperature=0.0,
            ),
        )
    except Exception as exc:
        logger.warning("LLM classification call failed for %r: %s", raw, exc)
        return None

    if response.parsed is None:
        logger.warning("LLM returned no parsed result for %r: %r", raw, response.text)
        return None

    if isinstance(response.parsed, LLMIngredientClassification):
        return response.parsed
    return LLMIngredientClassification.model_validate(response.parsed)


async def _persist_classification(
    session: AsyncSession, classification: LLMIngredientClassification
) -> Ingredient:
    """Insert (or fetch) an Ingredient row for an LLM-classified entry."""
    canonical_slug = _slug(classification.canonical_name) or _slug(
        classification.canonical_name.replace(" ", "-")
    )
    if not canonical_slug:
        canonical_slug = "llm-classified-" + str(hash(classification.canonical_name))[:8]

    existing = await session.scalar(
        select(Ingredient).where(Ingredient.canonical_name == canonical_slug)
    )
    if existing is not None:
        return existing

    is_allergen = classification.category in {"dairy"} or any(
        "allergen" in c for c in classification.concerns
    )

    ingredient = Ingredient(
        canonical_name=canonical_slug,
        aliases=sorted(set(classification.aliases)),
        e_number=classification.e_number,
        category=classification.category,
        is_allergen=is_allergen,
        allergen_group=None,
        iarc_group=None,
        regulatory_flags={},
        common_concerns=sorted(set(classification.concerns)),
        notes=None,
        sources=[f"{LLM_SOURCE_PREFIX}{settings.gemini_vision_model}"],
    )
    session.add(ingredient)
    await session.commit()
    await session.refresh(ingredient)
    return ingredient


async def classify_unknowns(
    session: AsyncSession, unknown_matches: list[IngredientMatch]
) -> list[IngredientMatch]:
    """For each unmatched IngredientMatch, try LLM classification. Returns updated matches."""
    updated: list[IngredientMatch] = []
    for match in unknown_matches:
        if match.matched is not None:
            updated.append(match)
            continue

        cached = await _lookup_cached(session, match.raw)
        if cached is not None:
            updated.append(
                IngredientMatch(
                    raw=match.raw,
                    matched=cached,
                    score=100.0,
                    method="llm_cached",
                )
            )
            continue

        classification = await _classify_with_gemini(match.raw)
        if classification is None or not classification.is_real_food_ingredient:
            updated.append(match)
            continue

        ingredient = await _persist_classification(session, classification)
        updated.append(
            IngredientMatch(
                raw=match.raw,
                matched=ingredient,
                score=90.0,
                method="llm",
            )
        )

    return updated
