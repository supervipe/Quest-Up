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
from app.services.weekly_quest_service import WeeklyQuestService


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        items = await seed_avatar_items(db)
        await seed_quest_templates(db)
        await seed_achievements(db, items)
        await seed_npcs(db)
        await seed_weekly(db, items)
        await db.commit()


async def seed_avatar_items(db):
    existing_keys = set(await db.scalars(select(AvatarItem.pixel_asset_key)))
    rows = [
        item
        for item in avatar_item_seed_rows()
        if item.pixel_asset_key not in existing_keys
    ]
    if rows:
        db.add_all(rows)
        await db.flush()
    return {item.pixel_asset_key: item for item in await db.scalars(select(AvatarItem))}


def avatar_item_seed_rows() -> list[AvatarItem]:
    return [
        AvatarItem(name="Basic Shirt", item_type=AvatarItemType.body, pixel_asset_key="basic_shirt", price_coins=0, rarity=Rarity.common),
        AvatarItem(name="Adventurer Jacket", item_type=AvatarItemType.outfit, pixel_asset_key="adventurer_jacket", price_coins=120, rarity=Rarity.rare),
        AvatarItem(name="Explorer Hat", item_type=AvatarItemType.head, pixel_asset_key="explorer_hat", price_coins=60, rarity=Rarity.common),
        AvatarItem(name="Star Accessory", item_type=AvatarItemType.accessory, pixel_asset_key="star_accessory", price_coins=90, rarity=Rarity.rare),
        AvatarItem(name="Wooden Sword", item_type=AvatarItemType.weapon, pixel_asset_key="wooden_sword", price_coins=75, rarity=Rarity.common),
        AvatarItem(name="Trophy Badge", item_type=AvatarItemType.badge, pixel_asset_key="trophy_badge", price_coins=0, rarity=Rarity.epic, is_purchasable=False, is_reward_only=True),
        AvatarItem(name="Weekly Cape", item_type=AvatarItemType.outfit, pixel_asset_key="weekly_cape", price_coins=0, rarity=Rarity.epic, is_purchasable=False, is_reward_only=True),
        AvatarItem(name="Squire's Sword", item_type=AvatarItemType.accessory, pixel_asset_key="item_001", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Knight's Blade", item_type=AvatarItemType.accessory, pixel_asset_key="item_002", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Chef's Knife", item_type=AvatarItemType.accessory, pixel_asset_key="item_003", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Shadow Dagger", item_type=AvatarItemType.accessory, pixel_asset_key="item_004", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Frost Blade", item_type=AvatarItemType.accessory, pixel_asset_key="item_005", price_coins=600, rarity=Rarity.legendary),
        AvatarItem(name="Oak Staff", item_type=AvatarItemType.accessory, pixel_asset_key="item_006", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Red Rose", item_type=AvatarItemType.accessory, pixel_asset_key="item_007", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Carrot", item_type=AvatarItemType.accessory, pixel_asset_key="item_008", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Star Wand", item_type=AvatarItemType.accessory, pixel_asset_key="item_009", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Sapphire Scepter", item_type=AvatarItemType.accessory, pixel_asset_key="item_010", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Amethyst Scepter", item_type=AvatarItemType.accessory, pixel_asset_key="item_011", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Moonvine Staff", item_type=AvatarItemType.accessory, pixel_asset_key="item_012", price_coins=600, rarity=Rarity.legendary),
        AvatarItem(name="Bubble Tea", item_type=AvatarItemType.accessory, pixel_asset_key="item_013", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Swirl Lollipop", item_type=AvatarItemType.accessory, pixel_asset_key="item_014", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Hunter's Bow", item_type=AvatarItemType.accessory, pixel_asset_key="item_015", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Vine Bow", item_type=AvatarItemType.accessory, pixel_asset_key="item_016", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Ribbon Bow", item_type=AvatarItemType.accessory, pixel_asset_key="item_017", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Crossbow", item_type=AvatarItemType.accessory, pixel_asset_key="item_018", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Slingshot", item_type=AvatarItemType.accessory, pixel_asset_key="item_019", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Fishing Rod", item_type=AvatarItemType.accessory, pixel_asset_key="item_020", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Butterfly Net", item_type=AvatarItemType.accessory, pixel_asset_key="item_021", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Black Umbrella", item_type=AvatarItemType.accessory, pixel_asset_key="item_022", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Lace Parasol", item_type=AvatarItemType.accessory, pixel_asset_key="item_023", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Iron Lantern", item_type=AvatarItemType.accessory, pixel_asset_key="item_024", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Torch", item_type=AvatarItemType.accessory, pixel_asset_key="item_025", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Paper Kite", item_type=AvatarItemType.accessory, pixel_asset_key="item_026", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Balloon Puppy", item_type=AvatarItemType.accessory, pixel_asset_key="item_027", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Skateboard", item_type=AvatarItemType.accessory, pixel_asset_key="item_028", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Old Tome", item_type=AvatarItemType.accessory, pixel_asset_key="item_029", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Moon Tome", item_type=AvatarItemType.accessory, pixel_asset_key="item_030", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Leaf Tome", item_type=AvatarItemType.accessory, pixel_asset_key="item_031", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Gem Tome", item_type=AvatarItemType.accessory, pixel_asset_key="item_032", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Heart Tome", item_type=AvatarItemType.accessory, pixel_asset_key="item_033", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Retro Console", item_type=AvatarItemType.accessory, pixel_asset_key="item_034", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Flip Phone", item_type=AvatarItemType.accessory, pixel_asset_key="item_035", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Teddy Bear", item_type=AvatarItemType.accessory, pixel_asset_key="item_036", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Bunny Plush", item_type=AvatarItemType.accessory, pixel_asset_key="item_037", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Cat Plush", item_type=AvatarItemType.accessory, pixel_asset_key="item_038", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Shiba Plush", item_type=AvatarItemType.accessory, pixel_asset_key="item_039", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Rubber Duck", item_type=AvatarItemType.accessory, pixel_asset_key="item_040", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Snow Globe", item_type=AvatarItemType.accessory, pixel_asset_key="item_041", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Music Box", item_type=AvatarItemType.accessory, pixel_asset_key="item_042", price_coins=600, rarity=Rarity.legendary),
        AvatarItem(name="Heart Wand", item_type=AvatarItemType.accessory, pixel_asset_key="item_043", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Charm Wand", item_type=AvatarItemType.accessory, pixel_asset_key="item_044", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Candy Cane", item_type=AvatarItemType.accessory, pixel_asset_key="item_045", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Pinwheel", item_type=AvatarItemType.accessory, pixel_asset_key="item_046", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Sunflower", item_type=AvatarItemType.accessory, pixel_asset_key="item_047", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Cotton Candy", item_type=AvatarItemType.accessory, pixel_asset_key="item_048", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Sparkler", item_type=AvatarItemType.accessory, pixel_asset_key="item_049", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Glow Stick", item_type=AvatarItemType.accessory, pixel_asset_key="item_050", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Pink Balloon", item_type=AvatarItemType.accessory, pixel_asset_key="item_051", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Star Balloon", item_type=AvatarItemType.accessory, pixel_asset_key="item_052", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Paw Wand", item_type=AvatarItemType.accessory, pixel_asset_key="item_053", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Disco Ball", item_type=AvatarItemType.accessory, pixel_asset_key="item_054", price_coins=600, rarity=Rarity.legendary),
        AvatarItem(name="Retro Camera", item_type=AvatarItemType.accessory, pixel_asset_key="item_055", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Boombox", item_type=AvatarItemType.accessory, pixel_asset_key="item_056", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Pickaxe", item_type=AvatarItemType.accessory, pixel_asset_key="item_057", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Woodcutter Axe", item_type=AvatarItemType.accessory, pixel_asset_key="item_058", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Shovel", item_type=AvatarItemType.accessory, pixel_asset_key="item_059", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Sickle", item_type=AvatarItemType.accessory, pixel_asset_key="item_060", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Sledgehammer", item_type=AvatarItemType.accessory, pixel_asset_key="item_061", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Shuriken", item_type=AvatarItemType.accessory, pixel_asset_key="item_062", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Nunchucks", item_type=AvatarItemType.accessory, pixel_asset_key="item_063", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Spiked Flail", item_type=AvatarItemType.accessory, pixel_asset_key="item_064", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Wrench", item_type=AvatarItemType.accessory, pixel_asset_key="item_065", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Quest Scroll Kit", item_type=AvatarItemType.accessory, pixel_asset_key="item_066", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Green Elixir", item_type=AvatarItemType.accessory, pixel_asset_key="item_067", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Spray Can", item_type=AvatarItemType.accessory, pixel_asset_key="item_068", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Megaphone", item_type=AvatarItemType.accessory, pixel_asset_key="item_069", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Microphone", item_type=AvatarItemType.accessory, pixel_asset_key="item_070", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Bubble Blower", item_type=AvatarItemType.accessory, pixel_asset_key="item_071", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Potted Cactus", item_type=AvatarItemType.accessory, pixel_asset_key="item_072", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Aloe Plant", item_type=AvatarItemType.accessory, pixel_asset_key="item_073", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Coffee To-Go", item_type=AvatarItemType.accessory, pixel_asset_key="item_074", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Sprout Pouch", item_type=AvatarItemType.accessory, pixel_asset_key="item_075", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Watering Can", item_type=AvatarItemType.accessory, pixel_asset_key="item_076", price_coins=40, rarity=Rarity.common),
        AvatarItem(name="Soft Serve", item_type=AvatarItemType.accessory, pixel_asset_key="item_077", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Taiyaki", item_type=AvatarItemType.accessory, pixel_asset_key="item_078", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Jar & Ukulele", item_type=AvatarItemType.accessory, pixel_asset_key="item_079", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Pink Guitar", item_type=AvatarItemType.accessory, pixel_asset_key="item_080", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Violin", item_type=AvatarItemType.accessory, pixel_asset_key="item_081", price_coins=320, rarity=Rarity.epic),
        AvatarItem(name="Tambourine", item_type=AvatarItemType.accessory, pixel_asset_key="item_082", price_coins=90, rarity=Rarity.uncommon),
        AvatarItem(name="Pan Flute", item_type=AvatarItemType.accessory, pixel_asset_key="item_083", price_coins=180, rarity=Rarity.rare),
        AvatarItem(name="Sparrow", item_type=AvatarItemType.accessory, pixel_asset_key="item_084", price_coins=600, rarity=Rarity.legendary),
    ]


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
    await WeeklyQuestService().ensure_current_weekly(db)


if __name__ == "__main__":
    asyncio.run(seed())
