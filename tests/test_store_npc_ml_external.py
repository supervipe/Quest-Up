from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.constants import NPCOfferStatus
from app.core.database import utcnow
from app.models.avatar import AvatarItem
from app.models.npc import NPCQuestOffer, UserNPCSpawnState
from app.models.walking import WalkingSession

pytestmark = pytest.mark.asyncio


async def test_store_purchase_and_duplicate_rejected(client, auth_headers, db_session):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    from app.models.user import User

    user = await db_session.get(User, user_id)
    user.coins = 500
    await db_session.commit()
    item = await db_session.scalar(select(AvatarItem).where(AvatarItem.is_purchasable.is_(True), AvatarItem.price_coins > 0))

    bought = await client.post(f"/store/items/{item.id}/purchase", headers=auth_headers)
    assert bought.status_code == 200
    duplicate = await client.post(f"/store/items/{item.id}/purchase", headers=auth_headers)
    assert duplicate.status_code == 400


async def test_npc_does_not_spawn_before_three_minutes(client, auth_headers):
    start = await client.post("/walking/session/start", headers=auth_headers, json={"lat": 49.0, "lng": -123.0})
    session_id = start.json()["id"]
    update = await client.post("/walking/session/update", headers=auth_headers, json={"session_id": session_id, "lat": 49.001, "lng": -123.0, "speed_mps": 1.0})
    assert update.status_code == 200
    assert update.json()["npc_spawned"] is False


async def test_npc_acceptance_drops_spawn_chance(client, auth_headers, db_session):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    session = WalkingSession(user_id=user_id, started_at=utcnow() - timedelta(minutes=4), last_lat=49.0, last_lng=-123.0, total_distance_m=150)
    db_session.add(session)
    await db_session.commit()
    check = await client.post("/npc/spawn/check", headers=auth_headers)
    assert check.status_code == 200
    offer = await db_session.scalar(select(NPCQuestOffer).where(NPCQuestOffer.user_id == user_id, NPCQuestOffer.status == NPCOfferStatus.offered))
    if offer is None:
        pytest.skip("Spawn roll did not create an offer")
    accepted = await client.post(f"/npc/offers/{offer.id}/accept", headers=auth_headers)
    assert accepted.status_code == 200
    state = await db_session.scalar(select(UserNPCSpawnState).where(UserNPCSpawnState.user_id == user_id))
    assert float(state.current_spawn_chance) == 0.20
    assert state.cooldown_until is not None


async def test_ml_fallback_recommender(client, auth_headers):
    response = await client.post("/ml/recommend", headers=auth_headers, json={"lat": 49.2827, "lng": -123.1207, "limit": 3})
    assert response.status_code == 200
    assert len(response.json()) <= 3


async def test_external_mock_endpoints(client):
    weather = await client.get("/external/weather")
    places = await client.get("/external/places")
    assert weather.status_code == 200
    assert weather.json()["provider"] in {"open-meteo", "mock-fallback"}
    assert places.status_code == 200
    assert len(places.json()) >= 1
