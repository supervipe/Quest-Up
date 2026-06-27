from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.constants import MLEventType, QuestType
from app.core.database import Base, UUIDPrimaryKeyMixin, utcnow

JsonType = JSON().with_variant(JSONB, "postgresql")


class MLInteraction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ml_interactions"
    __table_args__ = (
        CheckConstraint("difficulty IS NULL OR difficulty BETWEEN 1 AND 5", name="ck_ml_interactions_difficulty"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_ml_interactions_rating"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_quest_id: Mapped[str | None] = mapped_column(ForeignKey("user_quests.id"), index=True)
    event_type: Mapped[MLEventType] = mapped_column(Enum(MLEventType, native_enum=False), index=True)
    quest_type: Mapped[QuestType | None] = mapped_column(Enum(QuestType, native_enum=False))
    difficulty: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[int | None] = mapped_column(Integer)
    context: Mapped[dict | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
