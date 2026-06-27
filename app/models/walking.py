from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDPrimaryKeyMixin, utcnow


class WalkingSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "walking_sessions"
    __table_args__ = (
        CheckConstraint("total_distance_m >= 0", name="ck_walking_sessions_distance"),
        CheckConstraint("last_lat IS NULL OR last_lat BETWEEN -90 AND 90", name="ck_walking_sessions_lat"),
        CheckConstraint("last_lng IS NULL OR last_lng BETWEEN -180 AND 180", name="ck_walking_sessions_lng"),
        CheckConstraint("(last_lat IS NULL) = (last_lng IS NULL)", name="ck_walking_sessions_coordinates_pair"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_walking_sessions_dates"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_lat: Mapped[float | None] = mapped_column(Numeric(10, 6))
    last_lng: Mapped[float | None] = mapped_column(Numeric(10, 6))
    last_movement_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_distance_m: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    npc_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    npc_spawned: Mapped[bool] = mapped_column(Boolean, default=False)
