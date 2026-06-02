from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserProfileUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_or_get_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    email_lower = payload.email.lower()

    existing = await session.scalar(select(User).where(User.email == email_lower))
    if existing is not None:
        return existing

    user = User(
        email=email_lower,
        display_name=payload.display_name,
        allergies=[],
        dietary_preferences=[],
        conditions=[],
        extra_profile={},
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/me", response_model=UserRead)
async def get_me(
    email: str = Query(..., description="The user's email (acts as identity)"),
    session: AsyncSession = Depends(get_session),
) -> User:
    email_lower = email.lower()
    user = await session.scalar(select(User).where(User.email == email_lower))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email {email_lower}",
        )
    return user


@router.put("/me/profile", response_model=UserRead)
async def update_my_profile(
    payload: UserProfileUpdate,
    email: str = Query(..., description="The user's email (acts as identity)"),
    session: AsyncSession = Depends(get_session),
) -> User:
    email_lower = email.lower()
    user = await session.scalar(select(User).where(User.email == email_lower))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email {email_lower}",
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return user
