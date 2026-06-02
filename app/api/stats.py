"""Public stats endpoint for the marketing/landing page."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.ingredient import Ingredient
from app.models.scan import Scan
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["system"])


class PublicStats(BaseModel):
    total_ingredients: int
    llm_classified_ingredients: int
    total_scans: int
    total_users: int


@router.get("", response_model=PublicStats)
async def public_stats(session: AsyncSession = Depends(get_session)) -> PublicStats:
    total_ingredients = await session.scalar(select(func.count(Ingredient.id))) or 0
    total_scans = await session.scalar(select(func.count(Scan.id))) or 0
    total_users = await session.scalar(select(func.count(User.id))) or 0

    llm_count_stmt = select(func.count(Ingredient.id)).where(
        Ingredient.sources.op("&&")(["llm:gemini-2.5-flash"])
    )
    llm_classified = await session.scalar(llm_count_stmt) or 0

    return PublicStats(
        total_ingredients=total_ingredients,
        llm_classified_ingredients=llm_classified,
        total_scans=total_scans,
        total_users=total_users,
    )
