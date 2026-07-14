from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JsonType = JSON().with_variant(JSONB, "postgresql")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("total_xp >= 0", name="ck_users_total_xp_nonnegative"),
        CheckConstraint("level >= 1", name="ck_users_level_positive"),
        CheckConstraint("coins >= 0", name="ck_users_coins_nonnegative"),
        CheckConstraint("current_streak >= 0", name="ck_users_current_streak_nonnegative"),
        CheckConstraint("longest_streak >= current_streak", name="ck_users_streak_order"),
        CheckConstraint("last_level_reward_claimed_for_level >= 1", name="ck_users_reward_level_positive"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_quest_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_level_reward_claimed_for_level: Mapped[int] = mapped_column(Integer, default=1)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", cascade="all, delete-orphan")
    stats: Mapped["UserStats"] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("preferred_radius_km > 0 AND preferred_radius_km <= 50", name="ck_profiles_radius"),
        CheckConstraint("preferred_difficulty IS NULL OR preferred_difficulty BETWEEN 1 AND 5", name="ck_profiles_difficulty"),
        CheckConstraint("home_lat IS NULL OR home_lat BETWEEN -90 AND 90", name="ck_profiles_lat"),
        CheckConstraint("home_lng IS NULL OR home_lng BETWEEN -180 AND 180", name="ck_profiles_lng"),
        CheckConstraint("(home_lat IS NULL) = (home_lng IS NULL)", name="ck_profiles_home_coordinates_pair"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    preferred_radius_km: Mapped[float] = mapped_column(Numeric(5, 2), default=5)
    preferred_difficulty: Mapped[int | None] = mapped_column(Integer)
    preferred_quest_types: Mapped[list[str]] = mapped_column(JsonType, default=lambda: ["location", "social", "action"])
    timezone: Mapped[str | None] = mapped_column(String(80))
    home_lat: Mapped[float | None] = mapped_column(Numeric(10, 6))
    home_lng: Mapped[float | None] = mapped_column(Numeric(10, 6))
    location_sharing_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    community_sharing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="profile")


class UserStats(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_stats"
    __table_args__ = (
        CheckConstraint("social_xp >= 0", name="ck_stats_social_xp"),
        CheckConstraint("creativity_xp >= 0", name="ck_stats_creativity_xp"),
        CheckConstraint("exploration_xp >= 0", name="ck_stats_exploration_xp"),
        CheckConstraint("knowledge_xp >= 0", name="ck_stats_knowledge_xp"),
        CheckConstraint("fitness_xp >= 0", name="ck_stats_fitness_xp"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    social_xp: Mapped[int] = mapped_column(Integer, default=0)
    creativity_xp: Mapped[int] = mapped_column(Integer, default=0)
    exploration_xp: Mapped[int] = mapped_column(Integer, default=0)
    knowledge_xp: Mapped[int] = mapped_column(Integer, default=0)
    fitness_xp: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="stats")
