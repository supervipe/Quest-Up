import asyncio
from datetime import timedelta

from sqlalchemy import select

from app.core.constants import AchievementCategory, AvatarItemType, QuestType, Rarity, StatCategory, WeeklyQuestStatus
from app.core.database import AsyncSessionLocal, utcnow
from app.models.achievement import Achievement
from app.models.avatar import AvatarItem
from app.models.community import WeeklyCommunityQuest
from app.models.npc import NPC
from app.models.quest import QuestTemplate


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        items = await seed_avatar_items(db)
        await seed_quest_templates(db)
        await seed_achievements(db, items)
        await seed_npcs(db)
        await seed_weekly(db, items)
        await db.commit()


async def seed_avatar_items(db):
    existing = await db.scalar(select(AvatarItem).where(AvatarItem.pixel_asset_key == "basic_shirt"))
    if existing:
        return {item.pixel_asset_key: item for item in await db.scalars(select(AvatarItem))}
    rows = [
        AvatarItem(name="Basic Shirt", item_type=AvatarItemType.body, pixel_asset_key="basic_shirt", price_coins=0, rarity=Rarity.common),
        AvatarItem(name="Adventurer Jacket", item_type=AvatarItemType.outfit, pixel_asset_key="adventurer_jacket", price_coins=120, rarity=Rarity.rare),
        AvatarItem(name="Explorer Hat", item_type=AvatarItemType.head, pixel_asset_key="explorer_hat", price_coins=60, rarity=Rarity.common),
        AvatarItem(name="Star Accessory", item_type=AvatarItemType.accessory, pixel_asset_key="star_accessory", price_coins=90, rarity=Rarity.rare),
        AvatarItem(name="Wooden Sword", item_type=AvatarItemType.weapon, pixel_asset_key="wooden_sword", price_coins=75, rarity=Rarity.common),
        AvatarItem(name="Trophy Badge", item_type=AvatarItemType.badge, pixel_asset_key="trophy_badge", price_coins=0, rarity=Rarity.epic, is_purchasable=False, is_reward_only=True),
        AvatarItem(name="Weekly Cape", item_type=AvatarItemType.outfit, pixel_asset_key="weekly_cape", price_coins=0, rarity=Rarity.epic, is_purchasable=False, is_reward_only=True),
    ]
    db.add_all(rows)
    await db.flush()
    return {item.pixel_asset_key: item for item in rows}


async def seed_quest_templates(db):
    if await db.scalar(select(QuestTemplate).where(QuestTemplate.title == "Visit a New Park")):
        return
    db.add_all([
        QuestTemplate(title="Visit a New Park", description_template="Walk to {place_name}, take in the space, and capture one photo that shows what made it worth the trip.", quest_type=QuestType.location, stat_category=StatCategory.exploration, base_difficulty=2, base_xp=45, base_coins=12, duration_minutes=30, requires_location=True, location_type="park", is_npc_eligible=True),
        QuestTemplate(title="Cafe Vibe Check", description_template="Find {place_name}, order something small, and note one detail that gives the place character.", quest_type=QuestType.location, stat_category=StatCategory.knowledge, base_difficulty=1, base_xp=30, base_coins=8, duration_minutes=20, requires_location=True, location_type="cafe"),
        QuestTemplate(title="Compliment Three People", description_template="Give three genuine compliments today and write down how the conversations felt.", quest_type=QuestType.social, stat_category=StatCategory.social, base_difficulty=3, base_xp=60, base_coins=18, duration_minutes=45, requires_location=False, is_npc_eligible=True),
        QuestTemplate(title="Sketch the View", description_template="Go to {place_name} and make a quick sketch or visual note from what you see.", quest_type=QuestType.action, stat_category=StatCategory.creativity, base_difficulty=2, base_xp=50, base_coins=14, duration_minutes=25, requires_location=True, location_type="mural"),
        QuestTemplate(title="Outdoor Fitness Burst", description_template="Visit {place_name}, do a short bodyweight routine, and take a photo of your quest spot.", quest_type=QuestType.action, stat_category=StatCategory.fitness, base_difficulty=3, base_xp=65, base_coins=20, duration_minutes=20, requires_location=True, location_type="park", is_npc_eligible=True, possible_item_reward_rarity=Rarity.common, item_reward_chance=0.1),
    ])


async def seed_achievements(db, items):
    if await db.scalar(select(Achievement).where(Achievement.name == "First Quest Complete")):
        return
    trophy = items["trophy_badge"]
    db.add_all([
        Achievement(name="First Quest Complete", description="Complete your first side quest.", icon_key="first_quest", category=AchievementCategory.milestone, condition_type="completed_quests", condition_value={"count": 1}, xp_bonus=25, coin_bonus=10),
        Achievement(name="3-Day Streak", description="Complete quests three days in a row.", icon_key="streak_3", category=AchievementCategory.streak, condition_type="streak", condition_value={"days": 3}, coin_bonus=15),
        Achievement(name="7-Day Streak", description="Complete quests seven days in a row.", icon_key="streak_7", category=AchievementCategory.streak, condition_type="streak", condition_value={"days": 7}, coin_bonus=40),
        Achievement(name="Social Starter", description="Complete five social quests.", icon_key="social_5", category=AchievementCategory.quest_type, condition_type="quest_type_completed", condition_value={"quest_type": "social", "count": 5}),
        Achievement(name="Explorer", description="Complete five location quests.", icon_key="location_5", category=AchievementCategory.quest_type, condition_type="quest_type_completed", condition_value={"quest_type": "location", "count": 5}),
        Achievement(name="Weekly Hero", description="Submit to a weekly quest.", icon_key="weekly_hero", category=AchievementCategory.weekly, condition_type="weekly_submission", condition_value={"count": 1}, item_reward_id=trophy.id),
        Achievement(name="NPC Friend", description="Accept your first NPC quest.", icon_key="npc_friend", category=AchievementCategory.npc, condition_type="npc_accept", condition_value={"count": 1}),
        Achievement(name="First Purchase", description="Buy your first avatar item.", icon_key="first_purchase", category=AchievementCategory.shop, condition_type="purchase", condition_value={"count": 1}),
    ])


async def seed_npcs(db):
    if await db.scalar(select(NPC).where(NPC.name == "Pixel Wanderer")):
        return
    db.add_all([
        NPC(name="Pixel Wanderer", personality="Curious, upbeat, and always on the move.", avatar_asset_key="npc_pixel_wanderer", spawn_weight=1.2),
        NPC(name="Cafe Bard", personality="Turns ordinary errands into tiny legends.", avatar_asset_key="npc_cafe_bard", spawn_weight=1.0),
        NPC(name="Park Ranger", personality="Knows every trail and shortcut.", avatar_asset_key="npc_park_ranger", spawn_weight=1.0),
        NPC(name="Street Artist", personality="Invites users to notice color, texture, and weird little details.", avatar_asset_key="npc_street_artist", spawn_weight=0.8),
    ])


async def seed_weekly(db, items):
    if await db.scalar(
        select(WeeklyCommunityQuest).where(
            WeeklyCommunityQuest.status == WeeklyQuestStatus.active,
            WeeklyCommunityQuest.starts_at <= utcnow(),
            WeeklyCommunityQuest.ends_at > utcnow(),
        )
    ):
        return
    db.add(WeeklyCommunityQuest(
        title="Neighborhood Snapshot Challenge",
        description="Take a photo that captures a hidden gem in your neighborhood and share it with the weekly community feed.",
        quest_type=QuestType.location,
        stat_category=StatCategory.exploration,
        xp_reward=120,
        coin_reward=50,
        reward_item_id=items["weekly_cape"].id,
        starts_at=utcnow(),
        ends_at=utcnow() + timedelta(days=7),
        status=WeeklyQuestStatus.active,
    ))


if __name__ == "__main__":
    asyncio.run(seed())
