import pytest
from sqlalchemy import select

from app.core.constants import MLEventType
from app.ml.feature_builder import MLFeatureBuilder
from app.ml.training import TrainingDatasetService
from app.models.ml import MLInteraction


pytestmark = pytest.mark.asyncio


async def test_event_label_rules():
    builder = MLFeatureBuilder()
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.accepted)).label == 1
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.completed)).label == 1
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.skipped)).label == 0
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.failed)).label == 0
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.rated, rating=5)).label == 1
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.rated, rating=1)).label == 0
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.rated, rating=3)).label is None
    assert builder.label_for_event(MLInteraction(user_id="u", event_type=MLEventType.shown)).label is None


async def test_training_dataset_exports_real_interaction_features(client, auth_headers, db_session):
    opened = await client.post(
        "/quests/session/open",
        headers=auth_headers,
        json={"lat": 49.2827, "lng": -123.1207, "timezone": "America/Vancouver"},
    )
    quest_id = opened.json()["normal"][0]["id"]
    await client.post(f"/quests/{quest_id}/accept", headers=auth_headers)
    await client.post(f"/quests/{quest_id}/complete", headers=auth_headers, json={"rating": 5})

    examples = await TrainingDatasetService().build_examples(db_session)

    assert examples
    labels = {example["label"] for example in examples}
    assert 1 in labels
    accepted = next(
        example
        for example in examples
        if example["event_features"]["event_type"] == MLEventType.accepted
    )
    assert accepted["schema_version"] == "quest_ranking_v1"
    assert accepted["user_features"]["level"] >= 1
    assert accepted["quest_features"]["quest_id"] == quest_id
    assert accepted["quest_features"]["quest_type"] in {"location", "social", "action"}
    assert "recent_positive_rate" in accepted["recent_behavior_features"]


async def test_training_preview_endpoint(client, auth_headers):
    opened = await client.post("/quests/session/open", headers=auth_headers, json={})
    quest_id = opened.json()["normal"][0]["id"]
    await client.post(f"/quests/{quest_id}/skip", headers=auth_headers)

    response = await client.post(
        "/ml/training/preview",
        headers=auth_headers,
        json={"include_unlabeled": False, "limit": 50},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "quest_ranking_v1"
    assert body["negative"] >= 1
    assert body["count"] == len(body["examples"])


async def test_shown_event_context_contains_generation_features(client, auth_headers, db_session):
    opened = await client.post(
        "/quests/session/open",
        headers=auth_headers,
        json={"lat": 49.2827, "lng": -123.1207, "timezone": "America/Vancouver"},
    )
    quest_id = opened.json()["normal"][0]["id"]
    event = await db_session.scalar(
        select(MLInteraction).where(
            MLInteraction.user_quest_id == quest_id,
            MLInteraction.event_type == MLEventType.shown,
        )
    )

    assert event is not None
    assert event.context["source"] == "normal"
    assert "rule_selection_score" in event.context
    assert "local_hour" in event.context
    assert "place_types" in event.context
