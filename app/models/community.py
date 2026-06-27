from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import QuestType, StatCategory, WeeklyQuestStatus
from app.core.database import Base, UUIDPrimaryKeyMixin, utcnow


class WeeklyCommunityQuest(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "weekly_community_quests"
    __table_args__ = (
        CheckConstraint("xp_reward >= 0", name="ck_weekly_quests_xp"),
        CheckConstraint("coin_reward >= 0", name="ck_weekly_quests_coins"),
        CheckConstraint("ends_at > starts_at", name="ck_weekly_quests_dates"),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quest_type: Mapped[QuestType] = mapped_column(Enum(QuestType, native_enum=False))
    stat_category: Mapped[StatCategory] = mapped_column(Enum(StatCategory, native_enum=False))
    xp_reward: Mapped[int] = mapped_column(Integer)
    coin_reward: Mapped[int] = mapped_column(Integer)
    reward_item_id: Mapped[str | None] = mapped_column(ForeignKey("avatar_items.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[WeeklyQuestStatus] = mapped_column(Enum(WeeklyQuestStatus, native_enum=False), default=WeeklyQuestStatus.active)


class CommunityPost(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "community_posts"
    __table_args__ = (CheckConstraint("likes_count >= 0", name="ck_community_posts_likes"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    weekly_quest_id: Mapped[str | None] = mapped_column(ForeignKey("weekly_community_quests.id"), index=True)
    user_quest_id: Mapped[str | None] = mapped_column(ForeignKey("user_quests.id"), index=True)
    photo_url: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
