import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MLEventType, QuestType
from app.models.ml import MLInteraction
from app.models.quest import UserQuest
from app.models.user import User, UserProfile
from app.ml.feature_builder import MLFeatureBuilder


class TrainingDatasetService:
    def __init__(self) -> None:
        self.features = MLFeatureBuilder()

    async def build_examples(
        self,
        db: AsyncSession,
        *,
        include_unlabeled: bool = False,
        limit: int | None = None,
    ) -> list[dict]:
        query = select(MLInteraction).order_by(MLInteraction.created_at.asc())
        if limit:
            query = query.limit(limit)
        events = list(await db.scalars(query))
        examples: list[dict] = []
        for event in events:
            example = await self.build_example(db, event)
            if example["label"] is None and not include_unlabeled:
                continue
            examples.append(example)
        return examples

    async def build_example(self, db: AsyncSession, event: MLInteraction) -> dict:
        user = await db.get(User, event.user_id)
        if not user:
            raise ValueError(f"Missing user for ML event {event.id}")
        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
        quest = await db.get(UserQuest, event.user_quest_id) if event.user_quest_id else None
        label = self.features.label_for_event(event)
        return {
            "schema_version": "quest_ranking_v1",
            "task": "quest_ranking",
            "example_id": event.id,
            "user_id": user.id,
            "user_quest_id": event.user_quest_id,
            "user_features": self.features.user_features(user, profile),
            "quest_features": self.features.quest_features(quest, event),
            "context_features": self.features.context_features(quest, event),
            "recent_behavior_features": await self.recent_behavior_features(db, user.id, event),
            "event_features": self.features.event_features(event),
            "label": label.label,
            "label_weight": label.weight,
            "label_reason": label.reason,
        }

    async def recent_behavior_features(
        self,
        db: AsyncSession,
        user_id: str,
        event: MLInteraction,
        limit: int = 20,
    ) -> dict:
        prior_events = list(
            await db.scalars(
                select(MLInteraction)
                .where(
                    MLInteraction.user_id == user_id,
                    MLInteraction.created_at < event.created_at,
                )
                .order_by(MLInteraction.created_at.desc())
                .limit(limit)
            )
        )
        counts = {quest_type.value: 0 for quest_type in QuestType}
        positives = {quest_type.value: 0 for quest_type in QuestType}
        negatives = {quest_type.value: 0 for quest_type in QuestType}
        ratings: list[int] = []
        for prior in prior_events:
            if prior.quest_type:
                key = prior.quest_type.value
                counts[key] += 1
                prior_label = self.features.label_for_event(prior).label
                if prior_label == 1:
                    positives[key] += 1
                elif prior_label == 0:
                    negatives[key] += 1
            if prior.rating is not None:
                ratings.append(prior.rating)
        return {
            "window_size": len(prior_events),
            "counts_by_type": counts,
            "positive_by_type": positives,
            "negative_by_type": negatives,
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "recent_positive_rate": self._rate(sum(positives.values()), len(prior_events)),
            "recent_negative_rate": self._rate(sum(negatives.values()), len(prior_events)),
        }

    def write_jsonl(self, path: Path, examples: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for example in examples:
                file.write(json.dumps(example, sort_keys=True) + "\n")

    def _rate(self, count: int, total: int) -> float:
        if total <= 0:
            return 0
        return round(count / total, 4)


def train_placeholder() -> str:
    return "Use TrainingDatasetService to export real ML examples once enough data exists."
