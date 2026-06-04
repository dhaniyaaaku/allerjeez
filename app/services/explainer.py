"""LLM-generated plain-English explanations for flagged ingredients.

Cache-first: every (canonical_name, flag_kind) is stored permanently in Postgres
after the first generation, so subsequent scans hit the cache with zero LLM cost.

Quota-tolerant: if Gemini errors out (rate limit, transient outage), the explainer
returns None instead of raising. Callers should treat None as 'no explanation
this time' and render the flag without one.
"""

from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.explanation import IngredientExplanation
from app.schemas.safety_report import IngredientFlag

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
BASE_BACKOFF_SECONDS = 1.5

# We use the cheaper Gemini Lite model for explanations to spread cost across quotas.
EXPLAINER_MODEL = getattr(settings, "gemini_explainer_model", None) or "gemini-2.5-flash-lite"

SYSTEM_INSTRUCTION = """You write SHORT plain-English explanations for flagged food ingredients
in a personal food safety app. Each explanation must:

1. Be 1-2 sentences total. Concise. No bullet points.
2. Answer two implicit questions: "What is this ingredient?" and "Why is it flagged?"
3. Be conservative and factual. Do NOT make medical claims, dosage recommendations,
   or absolute warnings. Use phrases like "linked to", "classified as", "associated with".
4. Cite the regulatory authority when relevant (FDA, EFSA, IARC, WHO).
5. If the flag is a personal allergy, mention that briefly.
6. Never recommend the user eat or avoid anything. The system handles that elsewhere.

Output ONLY the explanation text. No prefixes, no quotes."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _build_prompt(flag: IngredientFlag) -> str:
    parts = [
        f'Ingredient (canonical name): "{flag.ingredient_name}"',
        f'How it appeared on the label: "{flag.raw_text_from_label}"',
        f'Flag category: {_describe_flag_kind(flag)}',
        f'Severity: {flag.severity}',
        f'Reason it was flagged: "{flag.reason}"',
    ]
    if flag.sources:
        parts.append("Sources for context: " + "; ".join(flag.sources[:3]))
    parts.append("\nWrite the 1-2 sentence explanation:")
    return "\n".join(parts)


def _describe_flag_kind(flag: IngredientFlag) -> str:
    if flag.personalized:
        return "personal-allergen"
    reason_l = flag.reason.lower()
    if "iarc" in reason_l or "carcinogen" in reason_l:
        return "carcinogen"
    if "allergen" in reason_l:
        return "other-allergen"
    return "controversial-additive"


async def _generate_explanation(flag: IngredientFlag) -> str | None:
    """Call Gemini. Returns the explanation text, or None on quota / transient errors."""
    client = _get_client()

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=EXPLAINER_MODEL,
                contents=[_build_prompt(flag)],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                ),
            )
            text = (response.text or "").strip()
            if not text:
                return None
            return text
        except genai_errors.APIError as exc:
            last_error = exc
            code = getattr(exc, "code", None)
            if code not in RETRYABLE_STATUS_CODES or attempt == MAX_RETRIES - 1:
                logger.warning(
                    "explainer: gemini error (status %s), giving up: %s",
                    code, exc,
                )
                return None
            wait = BASE_BACKOFF_SECONDS * (2**attempt)
            logger.info(
                "explainer: retry %d after %.1fs (status %s)",
                attempt + 1, wait, code,
            )
            await asyncio.sleep(wait)
        except Exception as exc:
            logger.exception("explainer: unexpected error generating explanation: %s", exc)
            return None

    logger.warning("explainer: exhausted retries (%s)", last_error)
    return None


async def _get_cached(
    session: AsyncSession, canonical_name: str, flag_kind: str
) -> str | None:
    row = await session.scalar(
        select(IngredientExplanation).where(
            IngredientExplanation.canonical_name == canonical_name,
            IngredientExplanation.flag_kind == flag_kind,
        )
    )
    return row.explanation if row is not None else None


async def _persist(
    session: AsyncSession,
    canonical_name: str,
    flag_kind: str,
    explanation: str,
) -> None:
    existing = await session.scalar(
        select(IngredientExplanation).where(
            IngredientExplanation.canonical_name == canonical_name,
            IngredientExplanation.flag_kind == flag_kind,
        )
    )
    if existing is not None:
        return
    row = IngredientExplanation(
        canonical_name=canonical_name,
        flag_kind=flag_kind,
        explanation=explanation,
        source_model=EXPLAINER_MODEL,
    )
    session.add(row)
    await session.commit()


async def explain_flag(
    session: AsyncSession, flag: IngredientFlag
) -> str | None:
    """Return a plain-English explanation for this flag, using cache where possible.

    Returns None silently on quota / generation failure. Caller renders without
    an explanation in that case.
    """
    canonical_name = flag.ingredient_name
    flag_kind = _describe_flag_kind(flag)

    cached = await _get_cached(session, canonical_name, flag_kind)
    if cached is not None:
        return cached

    explanation = await _generate_explanation(flag)
    if explanation is None:
        return None

    try:
        await _persist(session, canonical_name, flag_kind, explanation)
    except Exception as exc:
        logger.warning("explainer: failed to persist cache row: %s", exc)

    return explanation


async def annotate_flags(
    session: AsyncSession, flags: list[IngredientFlag]
) -> None:
    """Populate `explanation` on each flag in-place. Skips flags that already
    have an explanation. Cache-first, sequential to respect rate limits."""
    for flag in flags:
        if flag.explanation:
            continue
        explanation = await explain_flag(session, flag)
        if explanation is not None:
            flag.explanation = explanation
