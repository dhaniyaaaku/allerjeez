from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(255))

    allergies: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    dietary_preferences: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    conditions: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    extra_profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
