from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import QuestSource, QuestStatus, QuestType, StatCategory, WeeklyQuestStatus
from app.core.database import utcnow
from app.models.avatar import AvatarItem
from app.models.community import WeeklyCommunityQuest
from app.models.quest import UserQuest
from app.models.user import User


class WeeklyQuestService:
    WEEKLY_DURATION = timedelta(days=7)
    QUEST_ROTATION = (
        {
            "title": "Neighborhood Snapshot Challenge",
            "description": "Take a photo that captures a hidden gem in your neighborhood and share it with the weekly community feed.",
            "quest_type": QuestType.location,
            "stat_category": StatCategory.exploration,
            "xp_reward": 120,
            "coin_reward": 50,
        },
        {
            "title": "Tiny Kindness Week",
            "description": "Complete a small act of kindness, then share the moment or story with the weekly community feed.",
            "quest_type": QuestType.social,
            "stat_category": StatCategory.social,
            "xp_reward": 130,
            "coin_reward": 55,
        },
        {
            "title": "Creative Field Notes",
            "description": "Make a quick sketch, note, or creative observation from somewhere outside your usual route and share it.",
            "quest_type": QuestType.action,
            "stat_category": StatCategory.creativity,
            "xp_reward": 125,
            "coin_reward": 50,
        },
        {
            "title": "Fresh Air Fitness",
            "description": "Do a short outdoor movement session and share the spot that helped you get moving this week.",
            "quest_type": QuestType.action,
            "stat_category": StatCategory.fitness,
            "xp_reward": 135,
            "coin_reward": 60,
        },
    )

    async def current_weekly(self, db: AsyncSession) -> WeeklyCommunityQuest | None:
        return await self.ensure_current_weekly(db)

    async def ensure_current_weekly(
        self,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> WeeklyCommunityQuest | None:
        now = now or utcnow()
        current = await self._active_current(db, now)
        if current:
            return current

        latest = await db.scalar(
            select(WeeklyCommunityQuest).order_by(WeeklyCommunityQuest.starts_at.desc())
        )
        if latest and self._aware(latest.starts_at) > now:
            return None

        starts_at = self._next_start_after_latest(latest, now)
        rotation_index = self._rotation_index(starts_at)
        quest_data = self.QUEST_ROTATION[rotation_index % len(self.QUEST_ROTATION)]
        reward_item_id = await self._weekly_reward_item_id(db)
        weekly = WeeklyCommunityQuest(
            **quest_data,
            reward_item_id=reward_item_id,
            starts_at=starts_at,
            ends_at=starts_at + self.WEEKLY_DURATION,
            status=WeeklyQuestStatus.active,
        )
        db.add(weekly)
        await db.flush()
        return weekly

    async def _active_current(
        self,
        db: AsyncSession,
        now: datetime,
    ) -> WeeklyCommunityQuest | None:
        return await db.scalar(
            select(WeeklyCommunityQuest)
            .where(
                WeeklyCommunityQuest.status == WeeklyQuestStatus.active,
                WeeklyCommunityQuest.starts_at <= now,
                WeeklyCommunityQuest.ends_at > now,
            )
            .order_by(WeeklyCommunityQuest.starts_at.desc())
        )

    async def get_or_create_user_weekly(
        self,
        db: AsyncSession,
        user: User,
        weekly: WeeklyCommunityQuest | None,
    ) -> UserQuest | None:
        if not weekly:
            return None

        existing = await db.scalar(
            select(UserQuest)
            .where(
                UserQuest.user_id == user.id,
                UserQuest.source == QuestSource.weekly,
                UserQuest.context_snapshot["weekly_quest_id"].as_string() == weekly.id,
            )
            .order_by(UserQuest.assigned_at.desc())
        )
        if existing:
            return existing

        quest = UserQuest(
            user_id=user.id,
            template_id=None,
            source=QuestSource.weekly,
            generated_title=weekly.title,
            generated_description=weekly.description,
            quest_type=weekly.quest_type,
            stat_category=weekly.stat_category,
            difficulty=3,
            xp_reward=weekly.xp_reward,
            coin_reward=weekly.coin_reward,
            status=QuestStatus.active,
            expires_at=weekly.ends_at,
            context_snapshot={"weekly_quest_id": weekly.id},
            reward_item_id=weekly.reward_item_id,
        )
        db.add(quest)
        await db.flush()
        return quest

    async def _weekly_reward_item_id(self, db: AsyncSession) -> str | None:
        item = await db.scalar(
            select(AvatarItem).where(AvatarItem.pixel_asset_key == "weekly_cape")
        )
        return item.id if item else None

    def _next_start_after_latest(
        self,
        latest: WeeklyCommunityQuest | None,
        now: datetime,
    ) -> datetime:
        if not latest:
            return now
        starts_at = self._aware(latest.ends_at)
        while starts_at + self.WEEKLY_DURATION <= now:
            starts_at += self.WEEKLY_DURATION
        return starts_at

    def _rotation_index(self, starts_at: datetime) -> int:
        return int(self._aware(starts_at).timestamp() // int(self.WEEKLY_DURATION.total_seconds()))

    def _aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
