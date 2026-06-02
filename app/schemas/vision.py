from pydantic import BaseModel, Field


class ExtractedIngredients(BaseModel):
    """The structured output Gemini Vision returns from a food product image.

    Field order matters: Gemini follows the schema sequentially, so we ask it
    to decide "is this a food product?" before producing an ingredient list.
    """

    is_food_product: bool = Field(
        description=(
            "True only if the image clearly shows packaged food or an "
            "ingredient label. False for non-food images, unclear shots, "
            "screenshots of menus, etc."
        )
    )
    product_name: str | None = Field(
        default=None,
        description=(
            "The brand and/or product name as printed on the package. "
            "Null if not clearly visible."
        ),
    )
    language: str | None = Field(
        default=None,
        description=(
            "The primary language of the ingredient list on the package "
            "(e.g., 'english', 'hindi', 'mixed-english-hindi'). Null if "
            "no readable text."
        ),
    )
    ingredients: list[str] = Field(
        default_factory=list,
        description=(
            "Each ingredient as printed on the label, in order. Strip "
            "leading bullets/numbers/percentages. Preserve the original "
            "spelling. Empty list if no ingredients are visible."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Self-assessed confidence (0.0-1.0) in the extracted "
            "ingredient list given the image quality, label clarity, "
            "and language coverage."
        ),
    )
    notes: str | None = Field(
        default=None,
        description=(
            "Optional short note for the user explaining any extraction "
            "difficulty (blurry, partial label, foreign language, etc.). "
            "Null if extraction was clean."
        ),
    )
