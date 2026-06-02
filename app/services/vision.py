"""Gemini Vision wrapper for ingredient extraction.

Single public function: extract_ingredients_from_image(image_bytes, mime_type)
-> ExtractedIngredients (Pydantic-validated).
"""

from __future__ import annotations

import io
import logging

from google import genai
from google.genai import types
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.schemas.vision import ExtractedIngredients

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

EXTRACTION_PROMPT = """You are an ingredient list extractor for a food safety app.

Your task: look at the image and return a STRUCTURED JSON object describing the
food product's ingredient list. Follow these rules strictly:

1. EXTRACT ONLY what is visibly printed on the package. Never infer, guess, or
   add ingredients that are not clearly readable. It is better to return an
   empty list than to invent ingredients.

2. If the image does NOT clearly show a packaged food product or an ingredient
   label, set is_food_product=false and return an empty ingredients list.

3. For each ingredient, return the name as it appears on the label, including
   any E-numbers (e.g. "Sugar", "Sodium Benzoate (E211)", "Wheat Flour (Atta)").
   Preserve the original order.

4. Strip bullets, numbers, and weight percentages but keep parenthetical
   E-number annotations like "(E330)".

5. Report your confidence honestly. If the label is blurry, partially obscured,
   in a language you struggle with, or you had to skip text, lower the
   confidence and explain in `notes`.

Return JSON matching the provided schema exactly. No prose."""


def _validate_image(image_bytes: bytes, mime_type: str) -> None:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image too large: {len(image_bytes)} bytes "
            f"(limit: {MAX_IMAGE_BYTES} bytes / 5 MB)."
        )
    if not mime_type.startswith("image/"):
        raise ValueError(f"Not an image MIME type: {mime_type}")
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Could not parse image: {exc}") from exc


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def extract_ingredients_from_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> ExtractedIngredients:
    """Run the image through Gemini Vision and return a structured ingredient list.

    Raises ValueError on bad input. Raises google.genai exceptions on API failure.
    """
    _validate_image(image_bytes, mime_type)

    client = _get_client()
    response = await client.aio.models.generate_content(
        model=settings.gemini_vision_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedIngredients,
            temperature=0.0,
        ),
    )

    if response.parsed is None:
        raise RuntimeError(
            f"Gemini returned no parsed object. Raw text: {response.text!r}"
        )

    if not isinstance(response.parsed, ExtractedIngredients):
        # SDK sometimes returns dict instead of the model instance depending
        # on version; coerce defensively.
        return ExtractedIngredients.model_validate(response.parsed)

    return response.parsed
