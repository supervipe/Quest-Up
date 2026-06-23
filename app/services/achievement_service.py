from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ItemAcquiredFrom, QuestSource, QuestStatus, QuestType
from app.models.achievement import Achievement, UserAchievement
from app.models.avatar import UserAvatarItem
from app.models.community import CommunityPost
from app.models.quest import QuestCompletion, UserQuest
from app.models.user import User
from app.services.progression_calculator import ProgressionCalculator
from app.services.reward_service import RewardService


@dataclass(frozen=True)
class AchievementUnlock:
    achievement_id: str
    name: str
    xp_bonus: int
    coin_bonus: int
    item_awarded_id: str | None = None
    duplicate_item_id: str | None = None
    duplicate_compensation_coins: int = 0


@dataclass(frozen=True)
class AchievementEvaluationResult:
    unlocked: list[AchievementUnlock] = field(default_factory=list)
    xp_bonus: int = 0
    coin_bonus: int = 0
    duplicate_compensation_coins: int = 0


class AchievementService:
    def __init__(self) -> None:
        self.calculator = ProgressionCalculator()
        self.rewards = RewardService()

    async def evaluate_after_completion(
        self,
        db: AsyncSession,
        user: User,
        quest: UserQuest,
        shared_to_community: bool,
    ) -> AchievementEvaluationResult:
        existing_ids = set(
            await db.scalars(
                select(UserAchievement.achievement_id).where(
                    UserAchievement.user_id == user.id
                )
            )
        )
        achievements = list(
            await db.scalars(
                select(Achievement).where(Achievement.is_active.is_(True))
            )
        )
        unlocked: list[AchievementUnlock] = []
        xp_bonus = 0
        coin_bonus = 0
        duplicate_compensation = 0

        for achievement in achievements:
            if achievement.id in existing_ids:
                continue
            progress = await self._progress_for(db, user, quest, achievement, shared_to_community)
            if progress < 1:
                continue

            db.add(
                UserAchievement(
                    user_id=user.id,
                    achievement_id=achievement.id,
                    progress=progress,
                )
            )
            user.total_xp += achievement.xp_bonus
            user.coins += achievement.coin_bonus
            xp_bonus += achievement.xp_bonus
            coin_bonus += achievement.coin_bonus

            item_result = await self.rewards.award_achievement_item(
                db=db,
                user=user,
                item_id=achievement.item_reward_id,
                source_id=achievement.id,
            )
            duplicate_compensation += item_result.duplicate_compensation_coins
            unlocked.append(
                AchievementUnlock(
                    achievement_id=achievement.id,
                    name=achievement.name,
                    xp_bonus=achievement.xp_bonus,
                    coin_bonus=achievement.coin_bonus,
                    item_awarded_id=item_result.item_awarded_id,
                    duplicate_item_id=item_result.duplicate_item_id,
                    duplicate_compensation_coins=item_result.duplicate_compensation_coins,
                )
            )

        if xp_bonus:
            user.level = max(user.level, self.calculator.level_for_xp(user.total_xp))

        return AchievementEvaluationResult(
            unlocked=unlocked,
            xp_bonus=xp_bonus,
            coin_bonus=coin_bonus,
            duplicate_compensation_coins=duplicate_compensation,
        )

    async def _progress_for(
        self,
        db: AsyncSession,
        user: User,
        quest: UserQuest,
        achievement: Achievement,
        shared_to_community: bool,
    ) -> float:
        condition = achievement.condition_value or {}
        condition_type = achievement.condition_type

        if condition_type == "completed_quests":
            count = await self._completion_count(db, user.id)
            return self._ratio(count, condition.get("count", 1))

        if condition_type == "streak":
            return self._ratio(user.current_streak, condition.get("days", 1))

        if condition_type == "quest_type_completed":
            count = await self._completed_quest_type_count(
                db,
                user.id,
                condition.get("quest_type"),
            )
            return self._ratio(count, condition.get("count", 1))

        if condition_type == "weekly_submission":
            if quest.source == QuestSource.weekly and shared_to_community:
                return 1
            count = await self._community_submission_count(db, user.id)
            return self._ratio(count, condition.get("count", 1))

        if condition_type == "npc_accept":
            count = await self._npc_quest_count(db, user.id)
            return self._ratio(count, condition.get("count", 1))

        if condition_type == "purchase":
            count = await self._purchase_count(db, user.id)
            return self._ratio(count, condition.get("count", 1))

        return 0

    async def _completion_count(self, db: AsyncSession, user_id: str) -> int:
        return await db.scalar(
            select(func.count()).select_from(QuestCompletion).where(
                QuestCompletion.user_id == user_id
            )
        ) or 0

    async def _completed_quest_type_count(
        self,
        db: AsyncSession,
        user_id: str,
        quest_type: str | None,
    ) -> int:
        if not quest_type:
            return 0
        try:
            quest_type_filter = QuestType(quest_type)
        except ValueError:
            return 0
        return await db.scalar(
            select(func.count()).select_from(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.status == QuestStatus.completed,
                UserQuest.quest_type == quest_type_filter,
            )
        ) or 0

    async def _community_submission_count(self, db: AsyncSession, user_id: str) -> int:
        return await db.scalar(
            select(func.count()).select_from(CommunityPost).where(
                CommunityPost.user_id == user_id
            )
        ) or 0

    async def _npc_quest_count(self, db: AsyncSession, user_id: str) -> int:
        return await db.scalar(
            select(func.count()).select_from(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.source == QuestSource.npc,
            )
        ) or 0

    async def _purchase_count(self, db: AsyncSession, user_id: str) -> int:
        return await db.scalar(
            select(func.count()).select_from(UserAvatarItem).where(
                UserAvatarItem.user_id == user_id,
                UserAvatarItem.acquired_from == ItemAcquiredFrom.purchase,
            )
        ) or 0

    def _ratio(self, current: int, target: int) -> float:
        if target <= 0:
            return 1
        return min(current / target, 1)
