from math import floor

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import QuestStatus, RewardSource, VerificationStatus
from app.core.database import utcnow
from app.core.exceptions import bad_request, not_found
from app.models.avatar import ItemRewardEvent
from app.models.community import CommunityPost
from app.models.ml import MLInteraction
from app.models.quest import QuestCompletion, UserQuest
from app.models.user import User, UserStats


class ProgressionService:
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
    ) -> QuestCompletion:
        quest = await db.get(UserQuest, quest_id)
        if not quest or quest.user_id != user.id:
            raise not_found("Quest not found")
        if quest.status not in [QuestStatus.active, QuestStatus.accepted]:
            raise bad_request("Quest is not completable")
        xp = floor(quest.xp_reward * self._difficulty_multiplier(quest.difficulty) * self._streak_multiplier(user.current_streak))
        coins = quest.coin_reward
        user.total_xp += xp
        user.coins += coins
        user.current_streak = 1 if not user.last_quest_completed_at else user.current_streak + 1
        user.longest_streak = max(user.longest_streak, user.current_streak)
        user.last_quest_completed_at = utcnow()
        old_level = user.level
        user.level = self.level_for_xp(user.total_xp)
        if user.level > old_level:
            bonus = sum(25 + (level * 5) for level in range(old_level + 1, user.level + 1))
            user.coins += bonus
            db.add(ItemRewardEvent(user_id=user.id, coins_awarded=bonus, source=RewardSource.level_up, source_id=user.id))
        stats = await db.scalar(select(UserStats).where(UserStats.user_id == user.id))
        if stats:
            field = f"{quest.stat_category.value}_xp"
            setattr(stats, field, getattr(stats, field) + xp)
        quest.status = QuestStatus.completed
        quest.completed_at = utcnow()
        quest.verification_photo_url = photo_url
        quest.verification_status = VerificationStatus.accepted
        quest.user_rating = rating
        completion = QuestCompletion(
            user_quest_id=quest.id,
            user_id=user.id,
            photo_url=photo_url,
            caption=caption,
            completion_lat=lat,
            completion_lng=lng,
            completion_notes=notes,
            shared_to_community=shared_to_community,
            xp_awarded=xp,
            coins_awarded=coins,
            item_awarded_id=quest.reward_item_id,
        )
        db.add(completion)
        db.add(MLInteraction(user_id=user.id, user_quest_id=quest.id, event_type="completed", quest_type=quest.quest_type, difficulty=quest.difficulty, rating=rating, context={"source": quest.source.value}))
        if quest.source.value == "weekly" and shared_to_community and photo_url:
            db.add(CommunityPost(user_id=user.id, weekly_quest_id=quest.template_id, user_quest_id=quest.id, photo_url=photo_url, caption=caption))
        await db.commit()
        await db.refresh(completion)
        return completion

    def level_for_xp(self, xp: int) -> int:
        level = 1
        remaining = xp
        while remaining >= floor(100 * (1.15 ** (level - 1))):
            remaining -= floor(100 * (1.15 ** (level - 1)))
            level += 1
        return level

    def _difficulty_multiplier(self, difficulty: int) -> float:
        return {1: 1.0, 2: 1.15, 3: 1.35, 4: 1.6, 5: 2.0}.get(difficulty, 1.0)

    def _streak_multiplier(self, streak: int) -> float:
        if streak >= 30:
            return 2.0
        if streak >= 14:
            return 1.5
        if streak >= 7:
            return 1.25
        if streak >= 3:
            return 1.1
        return 1.0
