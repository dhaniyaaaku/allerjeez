from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Ingredient(Base, TimestampMixin):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)

    canonical_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    e_number: Mapped[str | None] = mapped_column(String(16), index=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True)

    is_allergen: Mapped[bool] = mapped_column(default=False, nullable=False)
    allergen_group: Mapped[str | None] = mapped_column(String(64))

    iarc_group: Mapped[str | None] = mapped_column(String(8), index=True)

    regulatory_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    common_concerns: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    notes: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
