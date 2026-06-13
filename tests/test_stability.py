import pytest

pytestmark = pytest.mark.asyncio


async def test_refresh_rotates_token_pair(client):
    registered = await client.post(
        "/auth/register",
        json={"email": "refresh@example.com", "password": "password123", "display_name": "Refresh Hero"},
    )
    assert registered.status_code == 200
    tokens = registered.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refreshed = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != tokens["access_token"]
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]


async def test_access_token_cannot_be_used_as_refresh_token(client):
    registered = await client.post(
        "/auth/register",
        json={"email": "wrong-refresh@example.com", "password": "password123", "display_name": "Hero"},
    )
    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": registered.json()["access_token"]},
    )
    assert response.status_code == 401


async def test_refresh_token_cannot_access_protected_routes(client):
    registered = await client.post(
        "/auth/register",
        json={"email": "refresh-auth@example.com", "password": "password123", "display_name": "Hero"},
    )
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {registered.json()['refresh_token']}"},
    )
    assert response.status_code == 401


async def test_missing_quest_mutations_return_404(client, auth_headers):
    missing_id = "00000000-0000-0000-0000-000000000000"
    accepted = await client.post(f"/quests/{missing_id}/accept", headers=auth_headers)
    skipped = await client.post(f"/quests/{missing_id}/skip", headers=auth_headers)
    assert accepted.status_code == 404
    assert skipped.status_code == 404


async def test_user_cannot_mutate_another_users_quest(client, auth_headers):
    other = await client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "password123", "display_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    opened = await client.post("/quests/session/open", headers=other_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]

    response = await client.post(f"/quests/{quest_id}/skip", headers=auth_headers)
    assert response.status_code == 404


async def test_invalid_rating_and_coordinates_are_rejected(client, auth_headers):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    invalid_rating = await client.post(
        f"/quests/{quest_id}/complete",
        headers=auth_headers,
        json={"rating": 6},
    )
    unpaired_coordinates = await client.post(
        f"/quests/{quest_id}/complete",
        headers=auth_headers,
        json={"completion_lat": 49.2},
    )
    assert invalid_rating.status_code == 422
    assert unpaired_coordinates.status_code == 422


async def test_liveness_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
