"""Scan endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.scan import Scan
from app.models.user import User
from app.schemas.safety_report import SafetyReport
from app.schemas.vision import ExtractedIngredients
from app.services.explainer import annotate_flags
from app.services.ingredient_lookup import lookup_ingredients
from app.services.llm_ingredient_lookup import classify_unknowns
from app.services.safety_report import build_safety_report
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


@router.post("/analyze", response_model=SafetyReport)
async def analyze_upload(
    file: UploadFile = File(..., description="Photo of a food product."),
    email: str = Query(..., description="The user's email (acts as identity)."),
    session: AsyncSession = Depends(get_session),
) -> SafetyReport:
    """Full pipeline: extract via Gemini -> fuzzy-match -> personalize -> save scan."""

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

    email_lower = email.lower()
    user = await session.scalar(select(User).where(User.email == email_lower))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email {email_lower}",
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

    matches = await lookup_ingredients(session, extracted.ingredients)
    matches = await classify_unknowns(session, matches)
    report = build_safety_report(extraction=extracted, matches=matches, user=user)

    # Plain-English explanations for each flag — cache-first, gracefully skipped
    # when Gemini quota is exhausted (flags just render without an explanation).
    for flag_list in (
        report.personal_allergens,
        report.other_allergens,
        report.carcinogens,
        report.controversial_additives,
    ):
        await annotate_flags(session, flag_list)

    scan = Scan(
        user_id=user.id,
        extracted_ingredients=extracted.ingredients,
        safety_report=report.model_dump(mode="json"),
    )
    session.add(scan)
    await session.commit()

    return report


@router.get("/me", response_model=list[SafetyReport])
async def list_my_scans(
    email: str = Query(..., description="The user's email (acts as identity)."),
    session: AsyncSession = Depends(get_session),
) -> list[SafetyReport]:
    email_lower = email.lower()
    user = await session.scalar(select(User).where(User.email == email_lower))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email {email_lower}",
        )

    stmt = select(Scan).where(Scan.user_id == user.id).order_by(Scan.created_at.desc())
    scans = (await session.scalars(stmt)).all()
    return [SafetyReport.model_validate(s.safety_report) for s in scans]
