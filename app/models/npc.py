from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import NPCOfferStatus
from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class NPC(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "npcs"
    __table_args__ = (CheckConstraint("spawn_weight > 0", name="ck_npcs_spawn_weight"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    personality: Mapped[str | None] = mapped_column(Text)
    avatar_asset_key: Mapped[str] = mapped_column(String(120), nullable=False)
    spawn_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class NPCQuestOffer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "npc_quest_offers"
    __table_args__ = (
        CheckConstraint("xp_reward >= 0", name="ck_npc_offers_xp"),
        CheckConstraint("coin_reward >= 0", name="ck_npc_offers_coins"),
        CheckConstraint("expires_at > offered_at", name="ck_npc_offers_expiration"),
    )

    npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    quest_template_id: Mapped[str | None] = mapped_column(ForeignKey("quest_templates.id"))
    generated_title: Mapped[str] = mapped_column(Text)
    generated_description: Mapped[str] = mapped_column(Text)
    xp_reward: Mapped[int] = mapped_column(Integer)
    coin_reward: Mapped[int] = mapped_column(Integer)
    reward_item_id: Mapped[str | None] = mapped_column(ForeignKey("avatar_items.id"))
    status: Mapped[NPCOfferStatus] = mapped_column(Enum(NPCOfferStatus, native_enum=False), default=NPCOfferStatus.offered, index=True)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserNPCSpawnState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_npc_spawn_state"
    __table_args__ = (
        CheckConstraint("current_spawn_chance BETWEEN 0 AND 1", name="ck_npc_spawn_state_chance"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    current_spawn_chance: Mapped[float] = mapped_column(Numeric(4, 2), default=0.70)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_spawned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_offer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
