from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.constants import QuestSource, QuestStatus, QuestType, Rarity, StatCategory, VerificationStatus
from app.core.database import Base, UUIDPrimaryKeyMixin, utcnow

JsonType = JSON().with_variant(JSONB, "postgresql")


class QuestTemplate(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quest_templates"
    __table_args__ = (
        CheckConstraint("base_difficulty BETWEEN 1 AND 5", name="ck_quest_templates_difficulty"),
        CheckConstraint("base_xp >= 0", name="ck_quest_templates_xp"),
        CheckConstraint("base_coins >= 0", name="ck_quest_templates_coins"),
        CheckConstraint("duration_minutes IS NULL OR duration_minutes > 0", name="ck_quest_templates_duration"),
        CheckConstraint("min_user_level >= 1", name="ck_quest_templates_min_level"),
        CheckConstraint("item_reward_chance BETWEEN 0 AND 1", name="ck_quest_templates_reward_chance"),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description_template: Mapped[str] = mapped_column(Text, nullable=False)
    quest_type: Mapped[QuestType] = mapped_column(Enum(QuestType, native_enum=False), index=True)
    stat_category: Mapped[StatCategory] = mapped_column(Enum(StatCategory, native_enum=False), index=True)
    base_difficulty: Mapped[int] = mapped_column(Integer)
    base_xp: Mapped[int] = mapped_column(Integer)
    base_coins: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    requires_location: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_photo: Mapped[bool] = mapped_column(Boolean, default=True)
    location_type: Mapped[str | None] = mapped_column(String(80), index=True)
    weather_conditions: Mapped[dict | None] = mapped_column(JsonType)
    time_windows: Mapped[dict | None] = mapped_column(JsonType)
    is_npc_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weekly_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    min_user_level: Mapped[int] = mapped_column(Integer, default=1)
    possible_item_reward_rarity: Mapped[Rarity | None] = mapped_column(Enum(Rarity, native_enum=False))
    item_reward_chance: Mapped[float] = mapped_column(Numeric(4, 3), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserQuest(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_quests"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_user_quests_difficulty"),
        CheckConstraint("xp_reward >= 0", name="ck_user_quests_xp_reward"),
        CheckConstraint("coin_reward >= 0", name="ck_user_quests_coin_reward"),
        CheckConstraint("user_rating IS NULL OR user_rating BETWEEN 1 AND 5", name="ck_user_quests_rating"),
        CheckConstraint("verification_score IS NULL OR verification_score BETWEEN 0 AND 100", name="ck_user_quests_verification_score"),
        CheckConstraint("target_lat IS NULL OR target_lat BETWEEN -90 AND 90", name="ck_user_quests_target_lat"),
        CheckConstraint("target_lng IS NULL OR target_lng BETWEEN -180 AND 180", name="ck_user_quests_target_lng"),
        CheckConstraint("(target_lat IS NULL) = (target_lng IS NULL)", name="ck_user_quests_target_coordinates_pair"),
        CheckConstraint("expires_at IS NULL OR expires_at > assigned_at", name="ck_user_quests_expiration"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("quest_templates.id"))
    source: Mapped[QuestSource] = mapped_column(Enum(QuestSource, native_enum=False), index=True)
    generated_title: Mapped[str] = mapped_column(Text)
    generated_description: Mapped[str] = mapped_column(Text)
    quest_type: Mapped[QuestType] = mapped_column(Enum(QuestType, native_enum=False), index=True)
    stat_category: Mapped[StatCategory] = mapped_column(Enum(StatCategory, native_enum=False))
    difficulty: Mapped[int] = mapped_column(Integer)
    xp_reward: Mapped[int] = mapped_column(Integer)
    coin_reward: Mapped[int] = mapped_column(Integer)
    status: Mapped[QuestStatus] = mapped_column(Enum(QuestStatus, native_enum=False), default=QuestStatus.active, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_lat: Mapped[float | None] = mapped_column(Numeric(10, 6))
    target_lng: Mapped[float | None] = mapped_column(Numeric(10, 6))
    target_place_name: Mapped[str | None] = mapped_column(String(160))
    target_place_type: Mapped[str | None] = mapped_column(String(80))
    weather_snapshot: Mapped[dict | None] = mapped_column(JsonType)
    context_snapshot: Mapped[dict | None] = mapped_column(JsonType)
    verification_photo_url: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False), default=VerificationStatus.pending)
    verification_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    user_rating: Mapped[int | None] = mapped_column(Integer)
    reward_item_id: Mapped[str | None] = mapped_column(ForeignKey("avatar_items.id"))


class QuestCompletion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quest_completions"
    __table_args__ = (
        CheckConstraint("xp_awarded >= 0", name="ck_quest_completions_xp"),
        CheckConstraint("coins_awarded >= 0", name="ck_quest_completions_coins"),
        CheckConstraint("completion_lat IS NULL OR completion_lat BETWEEN -90 AND 90", name="ck_quest_completions_lat"),
        CheckConstraint("completion_lng IS NULL OR completion_lng BETWEEN -180 AND 180", name="ck_quest_completions_lng"),
        CheckConstraint("(completion_lat IS NULL) = (completion_lng IS NULL)", name="ck_quest_completions_coordinates_pair"),
    )

    user_quest_id: Mapped[str] = mapped_column(ForeignKey("user_quests.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    photo_url: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    completion_lat: Mapped[float | None] = mapped_column(Numeric(10, 6))
    completion_lng: Mapped[float | None] = mapped_column(Numeric(10, 6))
    completion_notes: Mapped[str | None] = mapped_column(Text)
    shared_to_community: Mapped[bool] = mapped_column(Boolean, default=False)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    coins_awarded: Mapped[int] = mapped_column(Integer)
    item_awarded_id: Mapped[str | None] = mapped_column(ForeignKey("avatar_items.id"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
