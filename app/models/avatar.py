from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.constants import AvatarItemType, ItemAcquiredFrom, Rarity, RewardSource
from app.core.database import Base, UUIDPrimaryKeyMixin, utcnow

JsonType = JSON().with_variant(JSONB, "postgresql")


class AvatarItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "avatar_items"
    __table_args__ = (
        CheckConstraint("price_coins >= 0", name="ck_avatar_items_price"),
        CheckConstraint("unlock_level >= 1", name="ck_avatar_items_unlock_level"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    item_type: Mapped[AvatarItemType] = mapped_column(Enum(AvatarItemType, native_enum=False))
    pixel_asset_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    asset_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    price_coins: Mapped[int] = mapped_column(Integer, default=0)
    unlock_level: Mapped[int] = mapped_column(Integer, default=1)
    rarity: Mapped[Rarity] = mapped_column(Enum(Rarity, native_enum=False), default=Rarity.common)
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_reward_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserAvatarItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_avatar_items"
    __table_args__ = (UniqueConstraint("user_id", "avatar_item_id", name="uq_user_avatar_item"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    avatar_item_id: Mapped[str] = mapped_column(ForeignKey("avatar_items.id"), index=True)
    acquired_from: Mapped[ItemAcquiredFrom] = mapped_column(Enum(ItemAcquiredFrom, native_enum=False))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserAvatar(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_avatar"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    equipped_items: Mapped[dict] = mapped_column(JsonType, default=dict)
    base_style: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ItemRewardEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "item_reward_events"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    avatar_item_id: Mapped[str | None] = mapped_column(ForeignKey("avatar_items.id"))
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[RewardSource] = mapped_column(Enum(RewardSource, native_enum=False))
    source_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
