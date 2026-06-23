import pytest
from sqlalchemy import select

from app.core.constants import ItemAcquiredFrom, RewardSource
from app.models.achievement import Achievement, UserAchievement
from app.models.avatar import AvatarItem, ItemRewardEvent, UserAvatarItem
from app.models.quest import UserQuest
from app.models.user import User


@pytest.mark.asyncio
async def test_completion_awards_new_avatar_item(client, auth_headers, db_session):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    item = await db_session.scalar(
        select(AvatarItem).where(AvatarItem.pixel_asset_key == "trophy_badge")
    )
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    quest = await db_session.get(UserQuest, quest_id)
    quest.reward_item_id = item.id
    quest.xp_reward = 0
    quest.coin_reward = 0
    await db_session.commit()

    response = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={})

    assert response.status_code == 200
    result = response.json()
    assert result["item_awarded_id"] == item.id
    assert result["duplicate_item_id"] is None
    assert result["duplicate_compensation_coins"] == 0

    inventory = await db_session.scalar(
        select(UserAvatarItem).where(
            UserAvatarItem.user_id == user_id,
            UserAvatarItem.avatar_item_id == item.id,
        )
    )
    assert inventory is not None
    assert inventory.acquired_from == ItemAcquiredFrom.quest_reward

    reward_event = await db_session.scalar(
        select(ItemRewardEvent).where(
            ItemRewardEvent.user_id == user_id,
            ItemRewardEvent.avatar_item_id == item.id,
            ItemRewardEvent.source == RewardSource.quest_completion,
        )
    )
    assert reward_event is not None
    assert reward_event.coins_awarded == 0


@pytest.mark.asyncio
async def test_duplicate_completion_item_awards_compensation(client, auth_headers, db_session):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    item = await db_session.scalar(
        select(AvatarItem).where(AvatarItem.pixel_asset_key == "trophy_badge")
    )
    db_session.add(
        UserAvatarItem(
            user_id=user_id,
            avatar_item_id=item.id,
            acquired_from=ItemAcquiredFrom.quest_reward,
        )
    )
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    quest = await db_session.get(UserQuest, quest_id)
    quest.reward_item_id = item.id
    quest.xp_reward = 0
    quest.coin_reward = 0
    await db_session.commit()

    response = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={})

    assert response.status_code == 200
    result = response.json()
    assert result["item_awarded_id"] is None
    assert result["duplicate_item_id"] == item.id
    assert result["duplicate_compensation_coins"] == 60
    assert result["total_coins"] == 70

    user = await db_session.get(User, user_id)
    await db_session.refresh(user)
    assert user.coins == 70

    reward_event = await db_session.scalar(
        select(ItemRewardEvent).where(
            ItemRewardEvent.user_id == user_id,
            ItemRewardEvent.avatar_item_id == item.id,
            ItemRewardEvent.source == RewardSource.quest_completion,
        )
    )
    assert reward_event is not None
    assert reward_event.coins_awarded == 60


@pytest.mark.asyncio
async def test_first_completion_achievement_unlocks_once(client, auth_headers, db_session):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    first, second = opened.json()["normal"]
    first_quest = await db_session.get(UserQuest, first["id"])
    second_quest = await db_session.get(UserQuest, second["id"])
    first_quest.xp_reward = 0
    first_quest.coin_reward = 0
    second_quest.xp_reward = 0
    second_quest.coin_reward = 0
    await db_session.commit()

    first_response = await client.post(f"/quests/{first['id']}/complete", headers=auth_headers, json={})
    second_response = await client.post(f"/quests/{second['id']}/complete", headers=auth_headers, json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_result = first_response.json()
    second_result = second_response.json()
    assert first_result["achievement_xp_bonus"] == 25
    assert first_result["achievement_coin_bonus"] == 10
    assert [item["name"] for item in first_result["unlocked_achievements"]] == [
        "First Quest Complete"
    ]
    assert second_result["achievement_xp_bonus"] == 0
    assert second_result["achievement_coin_bonus"] == 0
    assert second_result["unlocked_achievements"] == []

    achievement = await db_session.scalar(
        select(Achievement).where(Achievement.name == "First Quest Complete")
    )
    unlocked = list(
        await db_session.scalars(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id,
            )
        )
    )
    assert len(unlocked) == 1
