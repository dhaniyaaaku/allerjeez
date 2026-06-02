"""Scan endpoints.

Today only the extraction step is wired up; lookup + safety report come on Day 6.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.vision import ExtractedIngredients
from app.services.vision import (
    MAX_IMAGE_BYTES,
    extract_ingredients_from_image,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scans"])

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


@router.post("/extract", response_model=ExtractedIngredients)
async def extract_from_upload(
    file: UploadFile = File(..., description="Photo of a food product."),
) -> ExtractedIngredients:
    """Upload a food product image. Returns the structured ingredient list
    extracted by Gemini Vision. No personalization, no DB write yet — that's Day 6."""

    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported content type: {file.content_type!r}. "
                f"Allowed: {sorted(ALLOWED_MIME_TYPES)}"
            ),
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Limit is {MAX_IMAGE_BYTES // (1024 * 1024)} MB.",
        )

    try:
        extracted = await extract_ingredients_from_image(
            image_bytes=image_bytes,
            mime_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Gemini extraction failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream LLM error: {exc}",
        ) from exc

    return extracted
