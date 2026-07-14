from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MLEventType, QuestSource, QuestStatus, RewardSource, VerificationStatus, WeeklyQuestStatus
from app.core.database import utcnow
from app.core.exceptions import bad_request, not_found
from app.models.avatar import ItemRewardEvent
from app.models.community import CommunityPost, WeeklyCommunityQuest
from app.models.ml import MLInteraction
from app.models.quest import QuestCompletion, UserQuest
from app.models.user import User, UserProfile, UserStats
from app.services.achievement_service import AchievementService
from app.services.progression_calculator import ProgressionCalculator
from app.services.reward_service import RewardService


class ProgressionService:
    def __init__(self) -> None:
        self.calculator = ProgressionCalculator()
        self.rewards = RewardService()
        self.achievements = AchievementService()

    async def complete_quest(
        self,
        db: AsyncSession,
        user: User,
        quest_id: str,
        photo_url: str | None,
        caption: str | None,
        lat: float | None,
        lng: float | None,
        notes: str | None,
        rating: int | None,
        shared_to_community: bool,
    ) -> dict:
        completed_at = utcnow()
        locked_user = await db.scalar(
            select(User)
            .where(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not locked_user:
            raise not_found("User not found")

        quest = await db.scalar(
            select(UserQuest)
            .where(UserQuest.id == quest_id, UserQuest.user_id == locked_user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not quest:
            raise not_found("Quest not found")
        if quest.expires_at and self._is_expired(quest.expires_at, completed_at):
            quest.status = QuestStatus.expired
            await db.commit()
            raise bad_request("Quest has expired")
        if quest.status not in [QuestStatus.active, QuestStatus.accepted]:
            raise bad_request("Quest is not completable")

        profile = await db.scalar(
            select(UserProfile).where(UserProfile.user_id == locked_user.id)
        )
        stats = await db.scalar(select(UserStats).where(UserStats.user_id == locked_user.id))
        if not stats:
            raise not_found("User stats not found")

        previous_level = locked_user.level
        calculation = self.calculator.calculate(
            base_xp=quest.xp_reward,
            difficulty=quest.difficulty,
            total_xp=locked_user.total_xp,
            previous_level=previous_level,
            claimed_reward_level=locked_user.last_level_reward_claimed_for_level,
            current_streak=locked_user.current_streak,
            last_completed_at=locked_user.last_quest_completed_at,
            completed_at=completed_at,
            timezone_name=profile.timezone if profile else None,
        )

        locked_user.total_xp += calculation.xp_awarded
        locked_user.level = calculation.new_level
        locked_user.coins += quest.coin_reward + calculation.level_up_coins
        locked_user.current_streak = calculation.current_streak
        locked_user.longest_streak = max(
            locked_user.longest_streak,
            calculation.current_streak,
        )
        locked_user.last_quest_completed_at = completed_at
        if calculation.new_level > locked_user.last_level_reward_claimed_for_level:
            locked_user.last_level_reward_claimed_for_level = calculation.new_level

        stat_field = f"{quest.stat_category.value}_xp"
        setattr(stats, stat_field, getattr(stats, stat_field) + calculation.xp_awarded)

        quest.status = QuestStatus.completed
        quest.completed_at = completed_at
        quest.verification_photo_url = photo_url
        quest.verification_status = VerificationStatus.accepted
        quest.user_rating = rating

        completion = QuestCompletion(
            user_quest_id=quest.id,
            user_id=locked_user.id,
            photo_url=photo_url,
            caption=caption,
            completion_lat=lat,
            completion_lng=lng,
            completion_notes=notes,
            shared_to_community=shared_to_community,
            xp_awarded=calculation.xp_awarded,
            coins_awarded=quest.coin_reward,
            item_awarded_id=quest.reward_item_id,
            completed_at=completed_at,
        )
        db.add(completion)
        db.add(
            MLInteraction(
                user_id=locked_user.id,
                user_quest_id=quest.id,
                event_type=MLEventType.completed,
                quest_type=quest.quest_type,
                difficulty=quest.difficulty,
                rating=rating,
                context={
                    "source": quest.source.value,
                    "template_id": quest.template_id,
                    "user_level_before_completion": previous_level,
                    "user_level_after_completion": locked_user.level,
                    "current_streak_after_completion": locked_user.current_streak,
                    "xp_awarded": calculation.xp_awarded,
                    "difficulty_multiplier": calculation.difficulty_multiplier,
                    "streak_multiplier": calculation.streak_multiplier,
                },
            )
        )
        if rating is not None:
            db.add(
                MLInteraction(
                    user_id=locked_user.id,
                    user_quest_id=quest.id,
                    event_type=MLEventType.rated,
                    quest_type=quest.quest_type,
                    difficulty=quest.difficulty,
                    rating=rating,
                    context={
                        "source": quest.source.value,
                        "template_id": quest.template_id,
                        "user_level": locked_user.level,
                    },
                )
            )

        quest_item_result = await self.rewards.award_quest_item(db, locked_user, quest)
        completion.item_awarded_id = quest_item_result.item_awarded_id
        duplicate_compensation_coins = quest_item_result.duplicate_compensation_coins

        if calculation.level_up_coins:
            db.add(
                ItemRewardEvent(
                    user_id=locked_user.id,
                    coins_awarded=calculation.level_up_coins,
                    source=RewardSource.level_up,
                    source_id=quest.id,
                )
            )

        if quest.source == QuestSource.weekly and shared_to_community:
            weekly_quest_id = self._weekly_quest_id_from_context(quest)
            if not weekly_quest_id:
                weekly_quest_id = await self._current_weekly_id(db)
            db.add(
                CommunityPost(
                    user_id=locked_user.id,
                    weekly_quest_id=weekly_quest_id,
                    user_quest_id=quest.id,
                    photo_url=photo_url,
                    caption=caption,
                )
            )

        achievement_result = await self.achievements.evaluate_after_completion(
            db=db,
            user=locked_user,
            quest=quest,
            shared_to_community=shared_to_community,
        )
        duplicate_compensation_coins += achievement_result.duplicate_compensation_coins

        await db.flush()
        result = {
            "id": completion.id,
            "xp_awarded": completion.xp_awarded,
            "coins_awarded": completion.coins_awarded,
            "level_up_coins": calculation.level_up_coins,
            "item_awarded_id": quest_item_result.item_awarded_id,
            "duplicate_item_id": quest_item_result.duplicate_item_id,
            "duplicate_compensation_coins": duplicate_compensation_coins,
            "achievement_xp_bonus": achievement_result.xp_bonus,
            "achievement_coin_bonus": achievement_result.coin_bonus,
            "unlocked_achievements": [
                {
                    "achievement_id": achievement.achievement_id,
                    "name": achievement.name,
                    "xp_bonus": achievement.xp_bonus,
                    "coin_bonus": achievement.coin_bonus,
                    "item_awarded_id": achievement.item_awarded_id,
                    "duplicate_item_id": achievement.duplicate_item_id,
                    "duplicate_compensation_coins": achievement.duplicate_compensation_coins,
                }
                for achievement in achievement_result.unlocked
            ],
            "shared_to_community": completion.shared_to_community,
            "previous_level": previous_level,
            "level": locked_user.level,
            "leveled_up": locked_user.level > previous_level,
            "total_xp": locked_user.total_xp,
            "total_coins": locked_user.coins,
            "current_streak": locked_user.current_streak,
            "longest_streak": locked_user.longest_streak,
        }
        await db.commit()
        return result

    def level_for_xp(self, xp: int) -> int:
        return self.calculator.level_for_xp(xp)

    def _is_expired(self, expires_at, completed_at) -> bool:
        return self.calculator._aware(expires_at) <= self.calculator._aware(completed_at)

    def _weekly_quest_id_from_context(self, quest: UserQuest) -> str | None:
        context = quest.context_snapshot or {}
        value = context.get("weekly_quest_id")
        return value if isinstance(value, str) else None

    async def _current_weekly_id(self, db: AsyncSession) -> str | None:
        weekly = await db.scalar(
            select(WeeklyCommunityQuest)
            .where(WeeklyCommunityQuest.status == WeeklyQuestStatus.active)
            .order_by(WeeklyCommunityQuest.starts_at.desc())
        )
        return weekly.id if weekly else None
