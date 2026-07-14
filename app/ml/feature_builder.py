from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.core.constants import MLEventType
from app.models.ml import MLInteraction
from app.models.quest import UserQuest
from app.models.user import User, UserProfile


@dataclass(frozen=True)
class EventLabel:
    label: int | None
    weight: float
    reason: str


class MLFeatureBuilder:
    positive_events = {MLEventType.accepted, MLEventType.completed}
    negative_events = {MLEventType.skipped, MLEventType.failed}

    def user_features(self, user: User, profile: UserProfile | None) -> dict:
        preferred = profile.preferred_quest_types if profile else ["location", "social", "action"]
        return {
            "level": user.level,
            "total_xp": user.total_xp,
            "coins": user.coins,
            "current_streak": user.current_streak,
            "longest_streak": user.longest_streak,
            "preferred_quest_types": preferred,
            "preferred_difficulty": profile.preferred_difficulty if profile else None,
            "preferred_radius_km": self._number(profile.preferred_radius_km) if profile else 5.0,
            "location_sharing_enabled": profile.location_sharing_enabled if profile else True,
            "community_sharing_enabled": profile.community_sharing_enabled if profile else False,
        }

    def quest_features(self, quest: UserQuest | None, event: MLInteraction | None = None) -> dict:
        if quest:
            return {
                "quest_id": quest.id,
                "template_id": quest.template_id,
                "source": quest.source.value,
                "quest_type": quest.quest_type.value,
                "stat_category": quest.stat_category.value,
                "difficulty": quest.difficulty,
                "xp_reward": quest.xp_reward,
                "coin_reward": quest.coin_reward,
                "status": quest.status.value,
                "has_target_location": quest.target_lat is not None and quest.target_lng is not None,
                "target_place_type": quest.target_place_type,
                "has_reward_item": quest.reward_item_id is not None,
            }
        return {
            "quest_id": None,
            "template_id": self._context_value(event, "template_id"),
            "source": self._context_value(event, "source"),
            "quest_type": event.quest_type.value if event and event.quest_type else None,
            "stat_category": None,
            "difficulty": event.difficulty if event else None,
            "xp_reward": None,
            "coin_reward": None,
            "status": None,
            "has_target_location": False,
            "target_place_type": None,
            "has_reward_item": False,
        }

    def context_features(self, quest: UserQuest | None, event: MLInteraction | None = None) -> dict:
        quest_context = quest.context_snapshot if quest and quest.context_snapshot else {}
        event_context = event.context if event and event.context else {}
        weather = quest.weather_snapshot if quest and quest.weather_snapshot else {}
        score_components = quest_context.get("score_components") or {}
        return {
            "local_hour": quest_context.get("local_hour") or event_context.get("local_hour"),
            "timezone": quest_context.get("timezone") or event_context.get("timezone"),
            "place_types": quest_context.get("place_types") or event_context.get("place_types") or [],
            "weather_condition": weather.get("condition") or event_context.get("weather_condition"),
            "rule_selection_score": quest_context.get("selection_score"),
            "rule_context_score": score_components.get("context"),
            "rule_preference_score": score_components.get("preference"),
            "rule_randomness_score": score_components.get("randomness"),
        }

    def event_features(self, event: MLInteraction) -> dict:
        return {
            "event_id": event.id,
            "event_type": event.event_type.value,
            "rating": event.rating,
            "created_at": self._iso(event.created_at),
        }

    def label_for_event(self, event: MLInteraction) -> EventLabel:
        if event.event_type in self.positive_events:
            return EventLabel(label=1, weight=1.0, reason=f"{event.event_type.value}_event")
        if event.event_type in self.negative_events:
            return EventLabel(label=0, weight=1.0, reason=f"{event.event_type.value}_event")
        if event.event_type == MLEventType.rated:
            if event.rating is None:
                return EventLabel(label=None, weight=0.0, reason="rating_missing")
            if event.rating >= 4:
                return EventLabel(label=1, weight=1.0, reason="high_rating")
            if event.rating <= 2:
                return EventLabel(label=0, weight=1.0, reason="low_rating")
            return EventLabel(label=None, weight=0.25, reason="neutral_rating")
        return EventLabel(label=None, weight=0.0, reason="unlabeled_event")

    def _context_value(self, event: MLInteraction | None, key: str):
        if not event or not event.context:
            return None
        return event.context.get(key)

    def _number(self, value) -> float | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _iso(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()


def build_features(context: dict) -> dict:
    return {
        "user_level": context.get("user_level", 1),
        "difficulty": context.get("difficulty", 1),
        "hour_of_day": context.get("hour_of_day", 12),
        "current_streak": context.get("current_streak", 0),
    }
