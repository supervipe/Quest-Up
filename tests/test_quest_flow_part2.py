from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.constants import MLEventType, RewardSource
from app.models.avatar import ItemRewardEvent
from app.models.ml import MLInteraction
from app.models.quest import UserQuest
from app.models.user import User, UserProfile, UserStats
from app.services.progression_calculator import ProgressionCalculator

def test_streak_uses_profile_timezone_calendar_days():
    calculator = ProgressionCalculator()
    last_completion = datetime(2026, 6, 21, 6, 30, tzinfo=timezone.utc)
    next_completion = datetime(2026, 6, 21, 7, 30, tzinfo=timezone.utc)

    streak = calculator.calculate_streak(
        current_streak=2,
        last_completed_at=last_completion,
        completed_at=next_completion,
        timezone_name="America/Vancouver",
    )
    assert streak == 3


def test_same_local_day_does_not_increment_streak():
    calculator = ProgressionCalculator()
    streak = calculator.calculate_streak(
        current_streak=4,
        last_completed_at=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
        completed_at=datetime(2026, 6, 22, 6, tzinfo=timezone.utc),
        timezone_name="America/Vancouver",
    )
    assert streak == 4


def test_missed_day_resets_streak():
    calculator = ProgressionCalculator()
    streak = calculator.calculate_streak(
        current_streak=10,
        last_completed_at=datetime(2026, 6, 18, 12, tzinfo=timezone.utc),
        completed_at=datetime(2026, 6, 21, 12, tzinfo=timezone.utc),
        timezone_name="America/Vancouver",
    )
    assert streak == 1


def test_xp_level_and_coin_formulas():
    calculator = ProgressionCalculator()
    calculation = calculator.calculate(
        base_xp=100,
        difficulty=3,
        total_xp=0,
        previous_level=1,
        claimed_reward_level=1,
        current_streak=2,
        last_completed_at=datetime(2026, 6, 20, 12, tzinfo=timezone.utc),
        completed_at=datetime(2026, 6, 21, 12, tzinfo=timezone.utc),
        timezone_name="UTC",
    )
    assert calculation.current_streak == 3
    assert calculation.xp_awarded == 148
    assert calculation.new_level == 2
    assert calculation.level_up_coins == 35
    assert calculator.xp_required_for_level(2) == 115
    assert calculator.level_for_xp(214) == 2
    assert calculator.level_for_xp(215) == 3


@pytest.mark.asyncio
async def test_completion_returns_and_persists_progression(client, auth_headers, db_session):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    profile = await db_session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile.timezone = "America/Vancouver"

    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    quest = await db_session.get(UserQuest, quest_id)
    quest.xp_reward = 100
    quest.difficulty = 1
    quest.coin_reward = 10
    stat_field = f"{quest.stat_category.value}_xp"
    await db_session.commit()

    response = await client.post(
        f"/quests/{quest_id}/complete",
        headers=auth_headers,
        json={"rating": 5},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["xp_awarded"] == 100
    assert result["coins_awarded"] == 10
    assert result["level_up_coins"] == 35
    assert result["previous_level"] == 1
    assert result["level"] == 2
    assert result["leveled_up"] is True
    assert result["achievement_xp_bonus"] == 25
    assert result["achievement_coin_bonus"] == 10
    assert result["total_xp"] == 125
    assert result["total_coins"] == 55
    assert result["current_streak"] == 1

    user = await db_session.get(User, user_id)
    stats = await db_session.scalar(select(UserStats).where(UserStats.user_id == user_id))
    await db_session.refresh(user)
    await db_session.refresh(stats)
    assert user.level == 2
    assert user.last_level_reward_claimed_for_level == 2
    assert user.total_xp == 125
    assert user.coins == 55
    assert getattr(stats, stat_field) == 100

    reward = await db_session.scalar(
        select(ItemRewardEvent).where(
            ItemRewardEvent.user_id == user_id,
            ItemRewardEvent.source == RewardSource.level_up,
        )
    )
    assert reward is not None
    assert reward.coins_awarded == 35

    events = list(
        await db_session.scalars(
            select(MLInteraction).where(MLInteraction.user_quest_id == quest_id)
        )
    )
    assert MLEventType.completed in {event.event_type for event in events}
    assert MLEventType.rated in {event.event_type for event in events}


@pytest.mark.asyncio
async def test_same_day_completion_does_not_repeat_streak_or_level_reward(
    client,
    auth_headers,
    db_session,
):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    first, second = opened.json()["normal"]
    first_quest = await db_session.get(UserQuest, first["id"])
    second_quest = await db_session.get(UserQuest, second["id"])
    first_quest.xp_reward = 100
    first_quest.difficulty = 1
    first_quest.coin_reward = 0
    second_quest.xp_reward = 0
    second_quest.difficulty = 1
    second_quest.coin_reward = 0
    await db_session.commit()

    first_result = await client.post(f"/quests/{first['id']}/complete", headers=auth_headers, json={})
    second_result = await client.post(f"/quests/{second['id']}/complete", headers=auth_headers, json={})
    assert first_result.status_code == 200
    assert second_result.status_code == 200
    assert first_result.json()["current_streak"] == 1
    assert second_result.json()["current_streak"] == 1
    assert first_result.json()["level_up_coins"] == 35
    assert second_result.json()["level_up_coins"] == 0

    rewards = list(
        await db_session.scalars(
            select(ItemRewardEvent).where(
                ItemRewardEvent.user_id == user_id,
                ItemRewardEvent.source == RewardSource.level_up,
            )
        )
    )
    assert len(rewards) == 1


@pytest.mark.asyncio
async def test_completed_quest_cannot_be_completed_twice(client, auth_headers):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    first = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={})
    second = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={})
    assert first.status_code == 200
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_expired_quest_cannot_be_completed(client, auth_headers, db_session):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    quest = await db_session.get(UserQuest, quest_id)
    quest.assigned_at = quest.assigned_at - timedelta(days=2)
    quest.expires_at = quest.expires_at - timedelta(days=2)
    await db_session.commit()

    response = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Quest has expired"
