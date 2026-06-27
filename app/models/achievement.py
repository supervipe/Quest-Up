from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.constants import AchievementCategory
from app.core.database import Base, UUIDPrimaryKeyMixin, utcnow

JsonType = JSON().with_variant(JSONB, "postgresql")


class Achievement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "achievements"

    name: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text)
    icon_key: Mapped[str] = mapped_column(String(80))
    category: Mapped[AchievementCategory] = mapped_column(Enum(AchievementCategory, native_enum=False))
    condition_type: Mapped[str] = mapped_column(String(80))
    condition_value: Mapped[dict] = mapped_column(JsonType)
    xp_bonus: Mapped[int] = mapped_column(Integer, default=0)
    coin_bonus: Mapped[int] = mapped_column(Integer, default=0)
    item_reward_id: Mapped[str | None] = mapped_column(ForeignKey("avatar_items.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserAchievement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[str] = mapped_column(ForeignKey("achievements.id"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    progress: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
