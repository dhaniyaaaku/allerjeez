from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IngredientExplanation(Base, TimestampMixin):
    """LLM-generated plain-English explanation for a flagged ingredient.

    Cached so we don't re-explain the same ingredient on every scan.
    Keyed on (canonical_name, flag_kind) so the same ingredient can have
    distinct explanations when flagged as an allergen vs. a carcinogen
    vs. a controversial additive.
    """

    __tablename__ = "ingredient_explanations"

    id: Mapped[int] = mapped_column(primary_key=True)

    canonical_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    flag_kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_model: Mapped[str] = mapped_column(String(64), nullable=False)
