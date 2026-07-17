import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ItemAcquiredFrom, QuestSource, Rarity, RewardSource
from app.models.avatar import AvatarItem, ItemRewardEvent, UserAvatarItem
from app.models.quest import QuestTemplate, UserQuest
from app.models.user import User


@dataclass(frozen=True)
class ItemRewardResult:
    item_awarded_id: str | None = None
    duplicate_item_id: str | None = None
    duplicate_compensation_coins: int = 0


class RewardService:
    rarity_compensation = {
        Rarity.common: 10,
        Rarity.uncommon: 15,
        Rarity.rare: 25,
        Rarity.epic: 60,
        Rarity.legendary: 120,
    }

    async def award_quest_item(
        self,
        db: AsyncSession,
        user: User,
        quest: UserQuest,
    ) -> ItemRewardResult:
        item = await self._quest_reward_item(db, quest)
        if not item:
            return ItemRewardResult()
        return await self.award_item(
            db=db,
            user=user,
            item=item,
            acquired_from=self._acquired_from(quest.source),
            source=self._reward_source(quest.source),
            source_id=quest.id,
        )

    async def award_achievement_item(
        self,
        db: AsyncSession,
        user: User,
        item_id: str | None,
        source_id: str,
    ) -> ItemRewardResult:
        if not item_id:
            return ItemRewardResult()
        item = await db.get(AvatarItem, item_id)
        if not item or not item.is_active:
            return ItemRewardResult()
        return await self.award_item(
            db=db,
            user=user,
            item=item,
            acquired_from=ItemAcquiredFrom.achievement,
            source=RewardSource.achievement,
            source_id=source_id,
        )

    async def award_item(
        self,
        db: AsyncSession,
        user: User,
        item: AvatarItem,
        acquired_from: ItemAcquiredFrom,
        source: RewardSource,
        source_id: str,
    ) -> ItemRewardResult:
        owned = await db.scalar(
            select(UserAvatarItem).where(
                UserAvatarItem.user_id == user.id,
                UserAvatarItem.avatar_item_id == item.id,
            )
        )
        if owned:
            compensation = self._duplicate_compensation(item)
            user.coins += compensation
            db.add(
                ItemRewardEvent(
                    user_id=user.id,
                    avatar_item_id=item.id,
                    coins_awarded=compensation,
                    source=source,
                    source_id=source_id,
                )
            )
            return ItemRewardResult(
                duplicate_item_id=item.id,
                duplicate_compensation_coins=compensation,
            )

        inventory = UserAvatarItem(
            user_id=user.id,
            avatar_item_id=item.id,
            acquired_from=acquired_from,
        )
        db.add(inventory)
        db.add(
            ItemRewardEvent(
                user_id=user.id,
                avatar_item_id=item.id,
                coins_awarded=0,
                source=source,
                source_id=source_id,
            )
        )
        return ItemRewardResult(item_awarded_id=item.id)

    async def _quest_reward_item(self, db: AsyncSession, quest: UserQuest) -> AvatarItem | None:
        if quest.reward_item_id:
            item = await db.get(AvatarItem, quest.reward_item_id)
            return item if item and item.is_active else None

        if not quest.template_id:
            return None
        template = await db.get(QuestTemplate, quest.template_id)
        if (
            not template
            or not template.possible_item_reward_rarity
            or float(template.item_reward_chance or 0) <= 0
            or random.random() > float(template.item_reward_chance)
        ):
            return None

        items = list(
            await db.scalars(
                select(AvatarItem).where(
                    AvatarItem.is_active.is_(True),
                    AvatarItem.rarity == template.possible_item_reward_rarity,
                )
            )
        )
        return random.choice(items) if items else None

    def _duplicate_compensation(self, item: AvatarItem) -> int:
        base = self.rarity_compensation.get(item.rarity, 10)
        if item.price_coins > 0:
            base = max(base, item.price_coins // 2)
        return base

    def _acquired_from(self, source: QuestSource) -> ItemAcquiredFrom:
        if source == QuestSource.weekly:
            return ItemAcquiredFrom.weekly_reward
        if source == QuestSource.npc:
            return ItemAcquiredFrom.npc_reward
        return ItemAcquiredFrom.quest_reward

    def _reward_source(self, source: QuestSource) -> RewardSource:
        if source == QuestSource.weekly:
            return RewardSource.weekly_completion
        if source == QuestSource.npc:
            return RewardSource.npc_completion
        return RewardSource.quest_completion
