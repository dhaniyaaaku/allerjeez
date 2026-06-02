"""Produce a personalized SafetyReport from extracted ingredients + user profile.

Rules-based for now. LLM-generated plain-English explanations come in Week 2.
"""

from __future__ import annotations

from app.models.user import User
from app.schemas.safety_report import IngredientFlag, SafetyReport
from app.schemas.vision import ExtractedIngredients
from app.services.ingredient_lookup import IngredientMatch

IARC_GROUP_SEVERITY = {
    "1": "high",
    "2A": "high",
    "2B": "medium",
    "3": "low",
    "4": "low",
}


def _flag_personal_allergen(match: IngredientMatch, user_allergies: set[str]) -> IngredientFlag | None:
    if match.matched is None or not match.matched.is_allergen:
        return None
    group = (match.matched.allergen_group or "").lower()
    user_allergies_lower = {a.lower() for a in user_allergies}
    if group not in user_allergies_lower:
        return None
    return IngredientFlag(
        ingredient_name=match.matched.canonical_name,
        raw_text_from_label=match.raw,
        severity="high",
        reason=f"You marked '{group}' as a personal allergy.",
        personalized=True,
        sources=match.matched.sources,
    )


def _flag_other_allergen(match: IngredientMatch) -> IngredientFlag | None:
    if match.matched is None or not match.matched.is_allergen:
        return None
    return IngredientFlag(
        ingredient_name=match.matched.canonical_name,
        raw_text_from_label=match.raw,
        severity="medium",
        reason=f"Common allergen (group: {match.matched.allergen_group}).",
        personalized=False,
        sources=match.matched.sources,
    )


def _flag_carcinogen(match: IngredientMatch) -> IngredientFlag | None:
    if match.matched is None or not match.matched.iarc_group:
        return None
    group = match.matched.iarc_group
    severity = IARC_GROUP_SEVERITY.get(group, "medium")
    reason = f"IARC Group {group}: " + {
        "1": "carcinogenic to humans.",
        "2A": "probably carcinogenic to humans.",
        "2B": "possibly carcinogenic to humans.",
        "3": "not classifiable as carcinogenic.",
        "4": "probably not carcinogenic.",
    }.get(group, f"classified as {group}.")
    return IngredientFlag(
        ingredient_name=match.matched.canonical_name,
        raw_text_from_label=match.raw,
        severity=severity,
        reason=reason,
        personalized=False,
        sources=match.matched.sources,
    )


def _flag_controversial_additive(match: IngredientMatch) -> IngredientFlag | None:
    if match.matched is None:
        return None
    if not match.matched.common_concerns:
        return None
    if match.matched.iarc_group:
        return None  # already handled as a carcinogen flag
    if match.matched.is_allergen:
        return None  # already handled as an allergen flag
    return IngredientFlag(
        ingredient_name=match.matched.canonical_name,
        raw_text_from_label=match.raw,
        severity="medium",
        reason="Concerns: " + ", ".join(match.matched.common_concerns) + ".",
        personalized=False,
        sources=match.matched.sources,
    )


def _compute_verdict(
    personal_allergens: list[IngredientFlag],
    carcinogens: list[IngredientFlag],
    controversial: list[IngredientFlag],
    extraction: ExtractedIngredients,
) -> str:
    if not extraction.is_food_product:
        return "unknown"
    if personal_allergens:
        return "avoid-for-you"
    high_severity_carc = any(f.severity == "high" for f in carcinogens)
    if high_severity_carc:
        return "avoid-for-you"
    if carcinogens or controversial:
        return "caution-for-you"
    return "safe-for-you"


def build_safety_report(
    *,
    extraction: ExtractedIngredients,
    matches: list[IngredientMatch],
    user: User,
) -> SafetyReport:
    user_allergies = set(user.allergies or [])

    personal_allergens: list[IngredientFlag] = []
    other_allergens: list[IngredientFlag] = []
    carcinogens: list[IngredientFlag] = []
    controversial: list[IngredientFlag] = []
    safe_known: list[str] = []
    unknown: list[str] = []

    seen_keys: set[tuple[str, str]] = set()
    seen_safe: set[str] = set()

    def _add_unique(target: list[IngredientFlag], flag: IngredientFlag) -> bool:
        key = (flag.ingredient_name, flag.raw_text_from_label)
        if key in seen_keys:
            return False
        seen_keys.add(key)
        target.append(flag)
        return True

    for match in matches:
        if match.matched is None:
            if match.raw.strip():
                unknown.append(match.raw)
            continue

        flagged = False

        personal = _flag_personal_allergen(match, user_allergies)
        if personal is not None:
            if _add_unique(personal_allergens, personal):
                flagged = True
            continue

        other = _flag_other_allergen(match)
        if other is not None:
            if _add_unique(other_allergens, other):
                flagged = True

        carc = _flag_carcinogen(match)
        if carc is not None:
            if _add_unique(carcinogens, carc):
                flagged = True
            continue

        contro = _flag_controversial_additive(match)
        if contro is not None:
            if _add_unique(controversial, contro):
                flagged = True

        if not flagged and match.matched.canonical_name not in seen_safe:
            seen_safe.add(match.matched.canonical_name)
            safe_known.append(match.matched.canonical_name)

    verdict = _compute_verdict(personal_allergens, carcinogens, controversial, extraction)

    return SafetyReport(
        product_name=extraction.product_name,
        overall_verdict=verdict,
        personal_allergens=personal_allergens,
        other_allergens=other_allergens,
        carcinogens=carcinogens,
        controversial_additives=controversial,
        safe_known_ingredients=safe_known,
        unknown_ingredients=unknown,
        extraction=extraction,
    )
