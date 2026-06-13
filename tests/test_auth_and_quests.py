import pytest
from sqlalchemy import select

from app.core.constants import QuestSource, QuestStatus
from app.models.quest import UserQuest

pytestmark = pytest.mark.asyncio


async def test_auth_register_login_and_me(client):
    register = await client.post("/auth/register", json={"email": "new@example.com", "password": "password123", "display_name": "New Hero"})
    assert register.status_code == 200
    token = register.json()["access_token"]

    login = await client.post("/auth/login", json={"email": "new@example.com", "password": "password123"})
    assert login.status_code == 200

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


async def test_app_open_topup_creates_two_normal_quests(client, auth_headers):
    response = await client.post("/quests/session/open", headers=auth_headers, json={"lat": 49.2827, "lng": -123.1207, "timezone": "America/Vancouver"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["normal"]) == 2
    assert body["weekly"] is not None


async def test_weekly_does_not_count_toward_normal_limit(client, auth_headers, db_session):
    await client.post("/quests/session/open", headers=auth_headers, json={})
    result = await db_session.scalars(select(UserQuest).where(UserQuest.source == QuestSource.normal, UserQuest.status == QuestStatus.active))
    assert len(list(result)) >= 2


async def test_quest_generation_uses_mock_nearby_place(client, auth_headers):
    response = await client.post("/quests/generate?lat=49.2827&lng=-123.1207", headers=auth_headers)
    assert response.status_code == 200
    quest = response.json()
    assert quest["target_place_name"] in [None, "Harbor Green Park", "Side Quest Cafe", "Community Library", "Hidden Mural Alley"]


async def test_quest_completion_awards_xp_and_coins(client, auth_headers):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    completed = await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={"photo_url": "local://photo.jpg", "rating": 5})
    assert completed.status_code == 200
    assert completed.json()["xp_awarded"] > 0
    me = await client.get("/auth/me", headers=auth_headers)
    assert me.json()["total_xp"] > 0
    assert me.json()["coins"] > 0
