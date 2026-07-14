from datetime import datetime

from app.ml.model_registry import load_quest_ranker
from app.models.quest import QuestTemplate, UserQuest
from app.models.user import User, UserProfile


class LiveQuestRanker:
    def __init__(self) -> None:
        self.model = load_quest_ranker()

    @property
    def available(self) -> bool:
        return self.model is not None

    @property
    def metadata(self) -> dict:
        return self.model.metadata if self.model else {}

    def score_templates(
        self,
        *,
        user: User,
        profile: UserProfile | None,
        templates: list[QuestTemplate],
        places: list[dict],
        weather: dict,
        local_time: datetime,
        recent_quests: list[UserQuest],
    ) -> dict[str, float]:
        if not self.model or not templates:
            return {}
        examples = [
            self._candidate_example(
                user=user,
                profile=profile,
                template=template,
                places=places,
                weather=weather,
                local_time=local_time,
                recent_quests=recent_quests,
            )
            for template in templates
        ]
        scores = self.model.score_examples(examples)
        return {template.id: score for template, score in zip(templates, scores, strict=True)}

    def _candidate_example(
        self,
        *,
        user: User,
        profile: UserProfile | None,
        template: QuestTemplate,
        places: list[dict],
        weather: dict,
        local_time: datetime,
        recent_quests: list[UserQuest],
    ) -> dict:
        recent_counts = {quest_type: 0 for quest_type in ["location", "social", "action"]}
        recent_positive = {quest_type: 0 for quest_type in ["location", "social", "action"]}
        for quest in recent_quests[:8]:
            key = quest.quest_type.value
            recent_counts[key] += 1
            if quest.status.value in {"accepted", "completed"}:
                recent_positive[key] += 1
        return {
            "schema_version": "quest_ranking_v1",
            "task": "quest_ranking",
            "user_features": {
                "level": user.level,
                "total_xp": user.total_xp,
                "coins": user.coins,
                "current_streak": user.current_streak,
                "longest_streak": user.longest_streak,
                "preferred_quest_types": profile.preferred_quest_types if profile else ["location", "social", "action"],
                "preferred_difficulty": profile.preferred_difficulty if profile else None,
                "preferred_radius_km": float(profile.preferred_radius_km) if profile else 5.0,
                "location_sharing_enabled": profile.location_sharing_enabled if profile else True,
                "community_sharing_enabled": profile.community_sharing_enabled if profile else False,
            },
            "context_features": {
                "local_hour": local_time.hour,
                "time_bucket": self._time_bucket(local_time.hour),
                "weather": weather.get("condition"),
                "weather_condition": weather.get("condition"),
                "nearby_place_types": sorted({place["place_type"] for place in places}),
                "place_types": sorted({place["place_type"] for place in places}),
            },
            "quest_features": {
                "quest_template_key": template.title.lower().replace(" ", "_"),
                "template_id": template.id,
                "quest_type": template.quest_type.value,
                "stat_category": template.stat_category.value,
                "base_difficulty": template.base_difficulty,
                "difficulty": template.base_difficulty,
                "base_xp": template.base_xp,
                "xp_reward": template.base_xp,
                "base_coins": template.base_coins,
                "coin_reward": template.base_coins,
                "duration_minutes": template.duration_minutes,
                "requires_location": template.requires_location,
                "requires_photo": template.requires_photo,
                "location_type": template.location_type,
                "has_reward_item": template.possible_item_reward_rarity is not None,
            },
            "recent_behavior_features": {
                "recent_counts": recent_counts,
                "recent_positive": recent_positive,
                "counts_by_type": recent_counts,
                "positive_by_type": recent_positive,
            },
        }

    def _time_bucket(self, hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 21:
            return "evening"
        return "night"
