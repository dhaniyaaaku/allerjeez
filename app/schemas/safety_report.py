from pydantic import BaseModel, Field

from app.schemas.vision import ExtractedIngredients


class IngredientFlag(BaseModel):
    """A single flagged ingredient with the reason it was flagged."""

    ingredient_name: str
    raw_text_from_label: str
    severity: str = Field(description="'high', 'medium', or 'low'")
    reason: str
    personalized: bool = Field(
        default=False,
        description="True if this flag is specific to the user's profile.",
    )
    sources: list[str] = Field(default_factory=list)


class SafetyReport(BaseModel):
    """The personalized safety analysis of a scanned food product."""

    product_name: str | None
    overall_verdict: str = Field(
        description="'safe-for-you', 'caution-for-you', 'avoid-for-you', or 'unknown'"
    )
    personal_allergens: list[IngredientFlag] = Field(default_factory=list)
    other_allergens: list[IngredientFlag] = Field(default_factory=list)
    carcinogens: list[IngredientFlag] = Field(default_factory=list)
    controversial_additives: list[IngredientFlag] = Field(default_factory=list)
    safe_known_ingredients: list[str] = Field(
        default_factory=list,
        description=(
            "Ingredients matched to the knowledge base with no concerns "
            "(e.g., sugar, salt, cocoa butter)."
        ),
    )
    unknown_ingredients: list[str] = Field(
        default_factory=list,
        description="Ingredients we couldn't match to the knowledge base.",
    )
    extraction: ExtractedIngredients
