from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.constants import MLEventType, QuestSource, QuestStatus
from app.core.database import utcnow
from app.models.ml import MLInteraction
from app.models.quest import UserQuest

pytestmark = pytest.mark.asyncio


async def _user_id(client, headers):
    response = await client.get("/auth/me", headers=headers)
    return response.json()["id"]


async def test_manual_generation_respects_normal_quest_limit(client, auth_headers):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    assert opened.status_code == 200
    assert len(opened.json()["normal"]) == 2

    response = await client.post("/quests/generate", headers=auth_headers)
    assert response.status_code == 409
    assert "limit reached" in response.json()["detail"].lower()


async def test_force_generation_is_explicit_development_override(client, auth_headers):
    await client.post("/quests/session/open", headers=auth_headers, json={})
    response = await client.post("/quests/generate?force=true", headers=auth_headers)
    assert response.status_code == 200


async def test_session_open_expires_stale_quest_and_tops_up(client, auth_headers, db_session):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    stale_id = opened.json()["normal"][0]["id"]
    stale = await db_session.get(UserQuest, stale_id)
    stale.assigned_at = utcnow() - timedelta(days=2)
    stale.expires_at = utcnow() - timedelta(minutes=1)
    await db_session.commit()

    reopened = await client.post("/quests/session/open", headers=auth_headers, json={})
    assert reopened.status_code == 200
    assert len(reopened.json()["normal"]) == 2
    assert stale_id not in {quest["id"] for quest in reopened.json()["normal"]}
    await db_session.refresh(stale)
    assert stale.status == QuestStatus.expired


async def test_topup_avoids_duplicate_active_templates(client, auth_headers, db_session):
    await client.post("/quests/session/open", headers=auth_headers, json={})
    user_id = await _user_id(client, auth_headers)
    quests = list(
        await db_session.scalars(
            select(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.source == QuestSource.normal,
                UserQuest.status == QuestStatus.active,
            )
        )
    )
    assert len(quests) == 2
    assert len({quest.template_id for quest in quests}) == 2


async def test_generation_records_score_context_and_shown_events(client, auth_headers, db_session):
    opened = await client.post(
        "/quests/session/open",
        headers=auth_headers,
        json={"lat": 49.2827, "lng": -123.1207, "timezone": "America/Vancouver"},
    )
    assert opened.status_code == 200
    user_id = await _user_id(client, auth_headers)
    quests = list(
        await db_session.scalars(
            select(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.source == QuestSource.normal,
            )
        )
    )
    assert all("score_components" in quest.context_snapshot for quest in quests)
    assert all(quest.context_snapshot["place_types"] for quest in quests)

    shown_events = list(
        await db_session.scalars(
            select(MLInteraction).where(
                MLInteraction.user_id == user_id,
                MLInteraction.event_type == MLEventType.shown,
            )
        )
    )
    assert len(shown_events) == 2
    assert {event.user_quest_id for event in shown_events} == {quest.id for quest in quests}


async def test_accept_and_skip_record_lifecycle_events(client, auth_headers, db_session):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    first, second = opened.json()["normal"]
    accepted = await client.post(f"/quests/{first['id']}/accept", headers=auth_headers)
    skipped = await client.post(f"/quests/{second['id']}/skip", headers=auth_headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"

    events = list(
        await db_session.scalars(
            select(MLInteraction).where(
                MLInteraction.user_quest_id.in_([first["id"], second["id"]]),
                MLInteraction.event_type.in_([MLEventType.accepted, MLEventType.skipped]),
            )
        )
    )
    assert {(event.user_quest_id, event.event_type) for event in events} == {
        (first["id"], MLEventType.accepted),
        (second["id"], MLEventType.skipped),
    }
