import asyncio
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.constants import QuestSource, QuestStatus, QuestType
from app.core.database import AsyncSessionLocal
from app.models.achievement import UserAchievement
from app.models.avatar import ItemRewardEvent, UserAvatar
from app.models.quest import QuestTemplate, UserQuest
from app.models.user import User, UserProfile, UserStats
from app.seed import seed
from app.services.auth_service import register_user
from app.services.progression_service import ProgressionService
from app.services.quest_generation_service import QuestGenerationService
from app.services.quest_lifecycle_service import QuestLifecycleService


DEMO_PASSWORD = "QuestFlowDemo123!"
VANCOUVER_LAT = 49.2827
VANCOUVER_LNG = -123.1207


async def main() -> None:
    await seed()
    created_at = datetime.now(timezone.utc)
    timestamp = created_at.strftime("%Y%m%d_%H%M%S")
    email = f"questflow.demo.{timestamp}@example.com"

    async with AsyncSessionLocal() as db:
        user, _, _ = await register_user(
            db,
            email=email,
            password=DEMO_PASSWORD,
            display_name="Quest Flow Demo User",
        )

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            raise RuntimeError("Demo user was not created")
        await configure_location_heavy_profile(db, user)
        location_result = await generate_and_complete_location_quest(db, user)
        social_results = await create_and_complete_social_quests(db, user, count=3)

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            raise RuntimeError("Demo user disappeared")
        report_path = await write_report(
            db=db,
            user=user,
            email=email,
            created_at=created_at,
            location_result=location_result,
            social_results=social_results,
        )

    print(f"Created demo user: {email}")
    print(f"Password: {DEMO_PASSWORD}")
    print(f"Report: {report_path}")


async def configure_location_heavy_profile(db, user: User) -> None:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    profile.preferred_quest_types = [QuestType.location.value]
    profile.preferred_radius_km = 5
    profile.preferred_difficulty = 2
    profile.timezone = "America/Vancouver"
    profile.home_lat = VANCOUVER_LAT
    profile.home_lng = VANCOUVER_LNG
    profile.location_sharing_enabled = True
    profile.community_sharing_enabled = True
    await db.commit()


async def generate_and_complete_location_quest(db, user: User) -> dict:
    generator = QuestGenerationService()
    lifecycle = QuestLifecycleService()
    progression = ProgressionService()

    selected = None
    for _ in range(8):
        quest = await generator.generate_normal_quest(
            db,
            user,
            lat=VANCOUVER_LAT,
            lng=VANCOUVER_LNG,
            timezone="America/Vancouver",
            force=True,
        )
        await db.commit()
        await db.refresh(quest)
        if quest.quest_type == QuestType.location:
            selected = quest
            break
        quest.status = QuestStatus.skipped
        await db.commit()

    if not selected:
        raise RuntimeError("Could not generate a location quest for the demo")

    await lifecycle.accept(db, user, selected)
    result = await progression.complete_quest(
        db=db,
        user=user,
        quest_id=selected.id,
        photo_url=None,
        caption="Completed as a text-only demo completion.",
        lat=VANCOUVER_LAT,
        lng=VANCOUVER_LNG,
        notes="The user began with location-focused preferences.",
        rating=4,
        shared_to_community=False,
    )
    return {"quest_id": selected.id, "completion": result}


async def create_and_complete_social_quests(db, user: User, count: int) -> list[dict]:
    templates = list(
        await db.scalars(
            select(QuestTemplate)
            .where(
                QuestTemplate.is_active.is_(True),
                QuestTemplate.quest_type == QuestType.social,
            )
            .order_by(QuestTemplate.title)
        )
    )
    if not templates:
        raise RuntimeError("No social quest templates are seeded")

    progression = ProgressionService()
    results = []
    for index in range(count):
        template = templates[index % len(templates)]
        quest = UserQuest(
            user_id=user.id,
            template_id=template.id,
            source=QuestSource.normal,
            generated_title=f"{template.title} #{index + 1}",
            generated_description=template.description_template.format(
                place_name="somewhere nearby"
            ),
            quest_type=template.quest_type,
            stat_category=template.stat_category,
            difficulty=template.base_difficulty,
            xp_reward=template.base_xp,
            coin_reward=template.base_coins,
            status=QuestStatus.accepted,
            context_snapshot={
                "scenario": "demo_social_interest",
                "reason": "Completed to show behavioral preference shifting social.",
            },
        )
        db.add(quest)
        await db.commit()
        await db.refresh(quest)
        result = await progression.complete_quest(
            db=db,
            user=user,
            quest_id=quest.id,
            photo_url=None,
            caption=None,
            lat=None,
            lng=None,
            notes="Social quest completed for the demo user's behavioral history.",
            rating=5,
            shared_to_community=False,
        )
        results.append({"quest_id": quest.id, "completion": result})
    return results


async def write_report(
    db,
    user: User,
    email: str,
    created_at: datetime,
    location_result: dict,
    social_results: list[dict],
) -> Path:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    stats = await db.scalar(select(UserStats).where(UserStats.user_id == user.id))
    quests = list(
        await db.scalars(
            select(UserQuest)
            .where(UserQuest.user_id == user.id)
            .order_by(UserQuest.assigned_at.asc())
        )
    )
    achievements = list(
        await db.scalars(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        )
    )
    reward_events = list(
        await db.scalars(
            select(ItemRewardEvent)
            .where(ItemRewardEvent.user_id == user.id)
            .order_by(ItemRewardEvent.created_at.asc())
        )
    )
    avatar = await db.scalar(select(UserAvatar).where(UserAvatar.user_id == user.id))
    completed = [quest for quest in quests if quest.status == QuestStatus.completed]
    type_counts = Counter(quest.quest_type.value for quest in completed)
    completion_results = [location_result, *social_results]

    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"demo_quest_flow_{created_at.strftime('%Y%m%d_%H%M%S')}.md"

    lines = [
        "# Quest Flow Demo User Report",
        "",
        "## User",
        "",
        f"- Email: `{email}`",
        f"- Password: `{DEMO_PASSWORD}`",
        f"- User ID: `{user.id}`",
        f"- Created at: `{created_at.isoformat()}`",
        f"- Final level: `{user.level}`",
        f"- Final total XP: `{user.total_xp}`",
        f"- Final coins: `{user.coins}`",
        f"- Current streak: `{user.current_streak}`",
        f"- Longest streak: `{user.longest_streak}`",
        "",
        "## Starting Preferences",
        "",
        f"- Preferred quest types: `{profile.preferred_quest_types if profile else []}`",
        f"- Preferred difficulty: `{profile.preferred_difficulty if profile else None}`",
        f"- Preferred radius km: `{float(profile.preferred_radius_km) if profile else None}`",
        f"- Home location: `{profile.home_lat}, {profile.home_lng}`",
        f"- Timezone: `{profile.timezone if profile else None}`",
        "",
        "## Behavior Signal",
        "",
        "The user started with location-heavy preferences, then completed more social quests than location quests.",
        "",
        f"- Completed location quests: `{type_counts.get('location', 0)}`",
        f"- Completed social quests: `{type_counts.get('social', 0)}`",
        f"- Completed action quests: `{type_counts.get('action', 0)}`",
        "",
        "This creates a behavioral history where social quests are the strongest completed quest type for this demo user.",
        "",
        "## Completed Quest Results",
        "",
        "| # | Quest | Type | XP | Quest Coins | Level Coins | Achievement XP | Achievement Coins | Items | Final Level | Final XP | Final Coins |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|",
    ]

    completed_by_id = {quest.id: quest for quest in completed}
    for index, entry in enumerate(completion_results, start=1):
        quest = completed_by_id[entry["quest_id"]]
        result = entry["completion"]
        items = result["item_awarded_id"] or ""
        if result["duplicate_item_id"]:
            items = f"duplicate {result['duplicate_item_id']} (+{result['duplicate_compensation_coins']} coins)"
        lines.append(
            "| "
            f"{index} | {quest.generated_title} | {quest.quest_type.value} | "
            f"{result['xp_awarded']} | {result['coins_awarded']} | {result['level_up_coins']} | "
            f"{result['achievement_xp_bonus']} | {result['achievement_coin_bonus']} | {items} | "
            f"{result['level']} | {result['total_xp']} | {result['total_coins']} |"
        )

    lines.extend(
        [
            "",
            "## Stats",
            "",
            f"- Social XP: `{stats.social_xp if stats else 0}`",
            f"- Creativity XP: `{stats.creativity_xp if stats else 0}`",
            f"- Exploration XP: `{stats.exploration_xp if stats else 0}`",
            f"- Knowledge XP: `{stats.knowledge_xp if stats else 0}`",
            f"- Fitness XP: `{stats.fitness_xp if stats else 0}`",
            "",
            "## Achievements And Reward Events",
            "",
            f"- Achievements unlocked: `{len(achievements)}`",
            f"- Reward events created: `{len(reward_events)}`",
            f"- Avatar record exists: `{avatar is not None}`",
            "",
            "## Notes",
            "",
            "- Quest photos were intentionally omitted to confirm the optional-photo completion flow.",
            "- The first quest was generated by the recommendation/generation service using location-heavy preferences.",
            "- The social quests were created as controlled demo completions to build a clear social-interest history.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    asyncio.run(main())
