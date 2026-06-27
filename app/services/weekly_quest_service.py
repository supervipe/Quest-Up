from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import QuestSource, QuestStatus, WeeklyQuestStatus
from app.core.database import utcnow
from app.models.community import WeeklyCommunityQuest
from app.models.quest import UserQuest
from app.models.user import User


class WeeklyQuestService:
    async def current_weekly(self, db: AsyncSession) -> WeeklyCommunityQuest | None:
        return await db.scalar(
            select(WeeklyCommunityQuest)
            .where(
                WeeklyCommunityQuest.status == WeeklyQuestStatus.active,
                WeeklyCommunityQuest.starts_at <= utcnow(),
                WeeklyCommunityQuest.ends_at > utcnow(),
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
