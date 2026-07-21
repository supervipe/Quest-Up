from datetime import timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.constants import QuestSource, WeeklyQuestStatus
from app.core.database import utcnow
from app.models.community import CommunityPost, WeeklyCommunityQuest
from app.models.quest import QuestCompletion, UserQuest


@pytest.mark.asyncio
async def test_session_open_creates_completable_weekly_user_quest(client, auth_headers, db_session):
    response = await client.post("/quests/session/open", headers=auth_headers, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["weekly"] is not None
    assert body["weekly"]["source"] == QuestSource.weekly
    assert body["weekly_community"] is not None

    quest = await db_session.get(UserQuest, body["weekly"]["id"])
    assert quest is not None
    assert quest.source == QuestSource.weekly
    assert quest.context_snapshot["weekly_quest_id"] == body["weekly_community"]["id"]


@pytest.mark.asyncio
async def test_normal_quest_completion_does_not_require_photo(client, auth_headers, db_session):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]

    response = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={})

    assert response.status_code == 200
    completion = await db_session.scalar(
        select(QuestCompletion).where(QuestCompletion.user_quest_id == quest_id)
    )
    assert completion is not None
    assert completion.photo_url is None


@pytest.mark.asyncio
async def test_weekly_completion_can_share_to_community_without_photo(client, auth_headers, db_session):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    weekly = opened.json()["weekly"]
    weekly_community = opened.json()["weekly_community"]

    response = await client.post(
        f"/quests/{weekly['id']}/complete",
        headers=auth_headers,
        json={"shared_to_community": True, "caption": "Finished it without a photo."},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["shared_to_community"] is True
    assert result["item_awarded_id"] == weekly_community["reward_item_id"]

    post = await db_session.scalar(
        select(CommunityPost).where(CommunityPost.user_quest_id == weekly["id"])
    )
    assert post is not None
    assert post.weekly_quest_id == weekly_community["id"]
    assert post.photo_url is None
    assert post.caption == "Finished it without a photo."


@pytest.mark.asyncio
async def test_manual_weekly_submission_accepts_optional_photo(client, auth_headers, db_session):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    weekly = opened.json()["weekly"]
    weekly_community = await db_session.scalar(select(WeeklyCommunityQuest))
    await client.post(f"/quests/{weekly['id']}/complete", headers=auth_headers, json={})

    response = await client.post(
        f"/community/weekly/{weekly_community.id}/submit",
        headers=auth_headers,
        json={"user_quest_id": weekly["id"], "caption": "Text-only submission"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["photo_url"] is None
    assert body["caption"] == "Text-only submission"


@pytest.mark.asyncio
async def test_current_weekly_rolls_over_when_seeded_week_has_expired(client, db_session):
    now = utcnow()
    expired = await db_session.scalar(select(WeeklyCommunityQuest))
    expired.starts_at = now - timedelta(days=14)
    expired.ends_at = now - timedelta(days=7)
    expired.status = WeeklyQuestStatus.active
    await db_session.commit()

    response = await client.get("/community/weekly/current")

    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["id"] != expired.id

    current = await db_session.get(WeeklyCommunityQuest, body["id"])
    assert _aware(current.starts_at) <= now
    assert _aware(current.ends_at) > now


@pytest.mark.asyncio
async def test_session_open_rolls_over_expired_weekly_before_user_quest(client, auth_headers, db_session):
    now = utcnow()
    expired = await db_session.scalar(select(WeeklyCommunityQuest))
    expired.starts_at = now - timedelta(days=14)
    expired.ends_at = now - timedelta(days=7)
    expired.status = WeeklyQuestStatus.active
    await db_session.commit()

    response = await client.post("/quests/session/open", headers=auth_headers, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["weekly"] is not None
    assert body["weekly_community"] is not None
    assert body["weekly_community"]["id"] != expired.id

    user_weekly = await db_session.get(UserQuest, body["weekly"]["id"])
    assert user_weekly.context_snapshot["weekly_quest_id"] == body["weekly_community"]["id"]


def _aware(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
