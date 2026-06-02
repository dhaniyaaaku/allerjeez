from typing import Literal

from pydantic import BaseModel, Field


class LLMIngredientClassification(BaseModel):
    """Gemini's classification of a single unknown ingredient.

    Used only as a FALLBACK for ingredients not present in the authoritative
    knowledge base. Results are cached to Postgres so subsequent scans hit
    the cache instead of calling the LLM again.
    """

    canonical_name: str = Field(
        description=(
            "A lowercase, hyphenated canonical name. Strip punctuation and "
            "marketing-speak. E.g. 'cocoa butter' -> 'cocoa-butter'."
        )
    )
    is_real_food_ingredient: bool = Field(
        description=(
            "True only if the input is a legitimate food/beverage ingredient. "
            "False for non-ingredient text (e.g. 'see back of pack', '38%')."
        )
    )
    category: Literal[
        "common-food",
        "additive",
        "preservative",
        "colorant",
        "sweetener",
        "emulsifier",
        "thickener",
        "antioxidant",
        "flavoring",
        "spice",
        "grain",
        "fat",
        "dairy",
        "meat",
        "produce",
        "other",
        "non-ingredient",
    ] = Field(description="Broad category. Use 'non-ingredient' if not real food.")
    has_known_concerns: bool = Field(
        description=(
            "True only if this ingredient has well-established safety or health "
            "concerns (controversial additives, banned in some countries, etc.). "
            "False for everyday foods like sugar or cocoa butter even if "
            "consumed in excess is unhealthy."
        )
    )
    concerns: list[str] = Field(
        default_factory=list,
        description=(
            "Short hyphenated tags for any concerns. E.g. "
            "['banned-in-eu', 'trans-fats']. Empty if has_known_concerns=false."
        ),
    )
    aliases: list[str] = Field(
        default_factory=list,
        description=(
            "Alternative names for this ingredient (e.g. 'sucrose' for sugar, "
            "'sodium chloride' for salt). Lowercase."
        ),
    )
    e_number: str | None = Field(
        default=None,
        description=(
            "European E-number if this is an E-numbered additive (e.g. 'E330'). "
            "Null otherwise."
        ),
    )
