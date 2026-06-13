from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ItemAcquiredFrom, MLEventType, RewardSource
from app.core.exceptions import bad_request, not_found
from app.models.avatar import AvatarItem, ItemRewardEvent, UserAvatar, UserAvatarItem
from app.models.ml import MLInteraction
from app.models.user import User


class StoreService:
    async def purchase(self, db: AsyncSession, user: User, item_id: str) -> UserAvatarItem:
        item = await db.get(AvatarItem, item_id)
        if not item:
            raise not_found("Item not found")
        owned = await db.scalar(select(UserAvatarItem).where(UserAvatarItem.user_id == user.id, UserAvatarItem.avatar_item_id == item.id))
        if owned:
            raise bad_request("User already owns this item")
        if not item.is_active or not item.is_purchasable or item.is_reward_only:
            raise bad_request("Item is not available for purchase")
        if user.level < item.unlock_level:
            raise bad_request("User level is too low for this item")
        if user.coins < item.price_coins:
            raise bad_request("Not enough coins")
        user.coins -= item.price_coins
        inventory = UserAvatarItem(user_id=user.id, avatar_item_id=item.id, acquired_from=ItemAcquiredFrom.purchase)
        db.add(inventory)
        db.add(ItemRewardEvent(user_id=user.id, avatar_item_id=item.id, coins_awarded=-item.price_coins, source=RewardSource.quest_completion, source_id=item.id))
        db.add(MLInteraction(user_id=user.id, event_type=MLEventType.purchased_item, context={"item_id": item.id}))
        await db.commit()
        await db.refresh(inventory)
        return inventory

    async def equip(self, db: AsyncSession, user: User, equipped_items: dict[str, str], base_style: str | None) -> UserAvatar:
        owned_ids = set(await db.scalars(select(UserAvatarItem.avatar_item_id).where(UserAvatarItem.user_id == user.id)))
        missing = [item_id for item_id in equipped_items.values() if item_id not in owned_ids]
        if missing:
            raise bad_request("Cannot equip items the user does not own")
        avatar = await db.scalar(select(UserAvatar).where(UserAvatar.user_id == user.id))
        if not avatar:
            avatar = UserAvatar(user_id=user.id)
            db.add(avatar)
        avatar.equipped_items = equipped_items
        avatar.base_style = base_style
        await db.commit()
        await db.refresh(avatar)
        return avatar
